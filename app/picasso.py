import asyncio
import os
import typing
from functools import partial
from pathlib import Path

import tenacity
import vertexai
from rich.console import Console
from vertexai.generative_models import (
    FunctionDeclaration,
    GenerationConfig,
    GenerativeModel,
    Tool,
    ChatSession, Part, Image,
)
from google.auth import default
from vertexai.preview.vision_models import ImageGenerationModel
from google.oauth2 import service_account

console = Console()


class PicassoChat:
    """
    A class to generate images and poems using the PICASSO model.
    """

    def __init__(self, images_folder: typing.Union[str, Path] = "images", credentials_file: str = None, **kwargs):
        """
        Initialize the PICASSO class with the required models.
        """

        # Fetch environment variables
        project_id = os.getenv("PROJECT_ID")
        location = os.getenv("LOCATION")

        # Check if required environment variables are present
        if not project_id or not location:
            raise ValueError("Please provide the project_id and location as environment variables")

        # Initialize credentials
        if credentials_file:
            credentials = service_account.Credentials.from_service_account_file(credentials_file)
        else:
            credentials, _ = default()

        # Initialize Vertex AI
        vertexai.init(project=project_id, location=location, credentials=credentials)

        self._images_gen_model = ImageGenerationModel.from_pretrained(
            kwargs.get("images_gen_model_name", "imagen-3.0-generate-001"),
        )
        self._poem_gen_model = GenerativeModel(
            model_name=kwargs.get("poem_gen_model_name", "gemini-1.5-flash"),
            generation_config=GenerationConfig(temperature=2.0),
        )
        self._chat_model = GenerativeModel(
            model_name=kwargs.get("chat_model_name", "gemini-1.5-flash"),
            tools=self.get_chat_tools()
        )
        self._images_folder = Path(images_folder)
        self._chat_session: ChatSession | None = None

    @property
    def generated_images(self):
        """
        Returns the generated images.
        """
        return [image_file for image_file in self._images_folder.iterdir()]

    @staticmethod
    def get_chat_tools():
        """
        Returns the tools definition for the chat model.
        :return:
        """
        generate_images_tool = FunctionDeclaration(
            name="generate_images",
            description="Generates an image based on the provided prompt.",
            parameters={
                "type": "object",
                "properties": {
                    "prompt": {"type": "string"},
                    "number_of_images": {
                        "type": "integer",
                        "description": "The number of images to generate as int.",
                    },
                },
                "required": ["prompt"],
            },
        )
        write_poem_tool = FunctionDeclaration(
            name="write_poem",
            description="Generates or write a poem about the provide prompt and images.",
            parameters={
                "type": "object",
                "properties": {"prompt": {"type": "string"}}
            },
        )
        return [Tool(function_declarations=[write_poem_tool, generate_images_tool])]

    @tenacity.retry(wait=tenacity.wait_fixed(2), stop=tenacity.stop_after_attempt(3), reraise=True)
    async def generate_images(
        self, prompt: str, **kwargs: dict
    ):
        """
        Generates an image based on the provided prompt.

        Args:
            prompt (str): The text to generate the image from.
            number_of_images (int): The number of images to generate.

        Returns:
            str: The path to the generated image.
        """
        try:
            # it uses Imagen2 under the hood
            if prompt is None:
                raise ValueError("prompt cannot be None")

            self._images_folder.mkdir(exist_ok=True, parents=True)
            for image in self._images_folder.iterdir():
                image.unlink()
            
            number_of_images = kwargs.get("number_of_images", 1)
            console.log(
                f"Generating {int(number_of_images)} images based on the prompt: {prompt}"
            )
            generate_images = partial(self._images_gen_model.generate_images,
                                      prompt=prompt,
                                      number_of_images=int(number_of_images),
                                      aspect_ratio="1:1",
                                      safety_filter_level="block_some",
                                      person_generation="allow_adult",
                                      add_watermark=True)
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, generate_images)
            for i, image in enumerate(response.images):
                image.save(str(self._images_folder / f"image_{i}.jpg"))
        except Exception as e:
            console.log(f"An error occurred: {e}")
            raise RuntimeError(f"Failed to generate images: {e}") from e

    @tenacity.retry(wait=tenacity.wait_fixed(2), stop=tenacity.stop_after_attempt(3), reraise=True)
    async def write_poem(self, prompt: str = None):
        """
        Generates a poem based on the provided prompt and images.

        Args:
            prompt (str): The text to generate the poem from.

        Returns:
            str: The generated poem.
        """
        try:
            image_files = list(Path(self._images_folder).iterdir())
            if not image_files:
                return "No images found in the images folder. "

            images = [
                Part.from_image(Image.load_from_file(str(image_file)))
                for image_file in image_files
            ]
            text_prompt = prompt + "," if prompt else ""
            full_prompt = [f"write a poem based on the following content: {text_prompt}"] + images
            response = await self._poem_gen_model.generate_content_async(full_prompt)
            return response.text
        except Exception as e:
            console.log(f"An error occurred during poem generation: {e}")
            raise RuntimeError(f"Failed to generate poem: {e}") from e


    def start_session(self):
        """
        Start the chat.
        """
        self._chat_session = self._chat_model.start_chat()

    async def send_message(self, message: str | list):
        """
        Send a message to the chat model.
        """
        stream_response = await self._chat_session.send_message_async(
            message, 
            stream=True
        )
        return stream_response

    def send_message_sync(self, message: str | list):
        """
        Send a message to the chat model.
        """
        stream_response = self._chat_session.send_message(message, stream=True)
        return stream_response


if __name__ == "__main__":
    PROJECT_ID = "build-with-ai-project"
    LOCATION = "us-central1"
    vertexai.init(project=PROJECT_ID, location=LOCATION)

    chat = PicassoChat()
    chat.start_session()
    while True:
        user_input = input("Enter a message: ")
        if user_input == "exit":
            break
        response = chat.send_message_sync(user_input)
        for part in response:
            console.log(part.text)
