
import chainlit as cl
from vertexai.generative_models import GenerationResponse, Part, Image
import os
import sys
sys.path.append(os.path.abspath('.'))
from app.picasso import PicassoChat




@cl.on_chat_start
async def start():
    """
    Start the chat when the application launches.
    """
    # replace with your own credentials file path, follow the instructions in the README
    chat = PicassoChat()
    chat.start_session()
    cl.user_session.set("chat", chat)
    await cl.Message(content="Welcome to the Picasso app!").send()


@cl.step(type="tool")
async def generate_images(prompt: str, **kwargs):
    """
    Generate images based on the given prompt.

    :param prompt: The prompt to generate images from.
    :return: A list of generated images.
    """
    chat = cl.user_session.get("chat")
    await chat.generate_images(prompt, **kwargs)
    return chat.generated_images


@cl.step(type="tool")
async def write_poem(**kwargs):
    """
    Generate a poem based on the given prompt.

    :param prompt: The prompt to generate the poem from.
    :return: The generated poem.
    """
    chat = cl.user_session.get("chat")
    return await chat.write_poem(**kwargs)


@cl.on_message
async def on_message_handler(message: cl.Message):
    """
    Handle incoming messages and generate appropriate responses.

    :param message: The incoming message.
    :return: None
    """
    try:

        text_prompt = message.content

        """
        Although the following commented code can create multimodal prompts that include images and text, 
        this functionality is currently disabled. The chat is currently designed to handle text prompts only 
        since the chat model has been configured with function-calling capabilities to support the image generation 
        and integration with Imagen 3(Google's image generation model). Unfortunately, function calling is not yet supported 
        for Gemini when non-text input.
        """

        # message_elements = message.elements
        # message_images = [element for element in message_elements if element.type == "image"]
        # images_parts = list(map(lambda x: Part.from_image(Image.load_from_file(x.path)), message_images))
        # multimodal_prompt = [text_prompt] + images_parts


        chat = cl.user_session.get("chat")
        stream_response = await chat.send_message(text_prompt)
        msg = cl.Message(content="")
        function_call = None

        async for response_part in stream_response:
            response_part: GenerationResponse
            message_part: Part = response_part.candidates[0].content.parts[0]

            if message_part.function_call:
                function_call = message_part.function_call
                break

            await msg.stream_token(response_part.text)
        await msg.update()
        if function_call:
            function_name = function_call.name
            function_args = {
                arg_name: arg_val for arg_name, arg_val in function_call.args.items()
            }
            print(function_name, function_args)

            if function_name == "generate_images":
                generated_images = await generate_images(**function_args)
                image_elements = [
                    cl.Image(path=str(image_file), name=f"image_{i}", display="inline")
                    for i, image_file in enumerate(generated_images)
                ]
                await cl.Message(
                    content="Here are the generated images:", elements=image_elements
                ).send()
            elif function_name == "write_poem":
                poem = await write_poem(**function_args)
                await cl.Message(content=f"Here is the generated poem: {poem}").send()
    except Exception as e:
        await cl.Message(content=f"An error occurred: {str(e)}").send()
        raise e

        
