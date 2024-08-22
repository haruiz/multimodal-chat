import asyncio
import typing
from pathlib import Path

import tenacity
import vertexai
from rich.console import Console
from vertexai.generative_models import (
    FunctionDeclaration,
    GenerationConfig,
    GenerativeModel,
    Tool,
    ChatSession,
    Part,
    Image,
)
from vertexai.preview.vision_models import ImageGenerationModel

console = Console()


class PicassoApp:
    """
    A class to generate images and poems using the PICASSO model.
    """

    def __init__(self, images_folder: typing.Union[str, Path] = "images"):
        """
        Initialize the PICASSO class with the required models.
        """
        self._images_gen_model = ImageGenerationModel.from_pretrained(
            "imagegeneration@006"
        )
        self._poem_gen_model = GenerativeModel(
            model_name="gemini-1.5-flash",
            generation_config=GenerationConfig(temperature=2.0),
        )
        self._chat_model = GenerativeModel(
            model_name="gemini-1.5-flash",
            generation_config=GenerationConfig(temperature=0),
            tools=self.get_chat_tools_def(),
        )
        self._images_folder = Path(images_folder)
        self._chat_session: ChatSession = None

    @property
    def generated_images(self):
        """
        Returns the generated images.
        """
        return [image_file for image_file in self._images_folder.iterdir()]

    @staticmethod
    def get_chat_tools_def():
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
            description="Generates a poem based on the provided prompt and images.",
            parameters={
                "type": "object",
                "properties": {"prompt": {"type": "string"}},
            },
        )
        return [Tool(function_declarations=[generate_images_tool, write_poem_tool])]

    @tenacity.retry(wait=tenacity.wait_fixed(2), stop=tenacity.stop_after_attempt(3))
    async def generate_images(
        self, prompt: str, number_of_images: typing.Union[int, float] = 4
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

            console.log(
                f"Generating {int(number_of_images)} images based on the prompt: {prompt}"
            )
            response = self._images_gen_model.generate_images(
                prompt=prompt,
                number_of_images=int(number_of_images),
                add_watermark=True,
            )
            for i, image in enumerate(response.images):
                image.save(str(self._images_folder / f"image_{i}.jpg"))
        except Exception as e:
            console.log(f"An error occurred: {e}")
            raise e

    @tenacity.retry(wait=tenacity.wait_fixed(2), stop=tenacity.stop_after_attempt(3))
    async def write_poem(self, prompt: str):
        """
        Generates a poem based on the provided prompt and images.

        Args:
            prompt (str): The text to generate the poem from.

        Returns:
            str: The generated poem.
        """
        try:
            if prompt is None:
                raise ValueError("prompt cannot be None")

            image_files = list(Path(self._images_folder).iterdir())
            if len(image_files) == 0:
                return "No images found. in the images folder."

            images = [
                Part.from_image(Image.load_from_file(image_file))
                for image_file in image_files
            ]
            prompt = [
                f"write a poem based on the following prompt: {prompt} and the images: "
            ] + images
            response = await self._poem_gen_model.generate_content_async(prompt)
            return response.text
        except Exception as e:
            console.log(f"An error occurred: {e}")
            raise e

    def start_chat(self):
        """
        Start the chat.
        """
        self._chat_session = self._chat_model.start_chat()

    async def send_message(self, message: str):
        """
        Send a message to the chat model.
        """
        stream_response = await self._chat_session.send_message_async(
            message, stream=True
        )
        return stream_response

    def send_message_sync(self, message: str):
        """
        Send a message to the chat model.
        """
        stream_response = self._chat_session.send_message(message, stream=True)
        return stream_response


if __name__ == "__main__":
    PROJECT_ID = "build-with-ai-project"
    LOCATION = "us-central1"
    vertexai.init(project=PROJECT_ID, location=LOCATION)

    app = PicassoApp()
    app.start_chat()
    while True:
        user_input = input("Enter a message: ")
        if user_input == "exit":
            break
        response = app.send_message_sync(user_input)
        for part in response:
            console.log(part.text)
