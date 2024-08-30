import chainlit as cl
from vertexai.generative_models import GenerationResponse, Part

from picasso import PicassoApp

app = PicassoApp()


@cl.on_chat_start
async def start():
    """
    Start the chat when the application launches.
    """
    app.start_chat()
    await cl.Message(content="Welcome to the Picasso app!").send()


@cl.step(type="tool")
async def generate_images(prompt: str, number_of_images: int):
    """
    Generate images based on the given prompt.

    :param prompt: The prompt to generate images from.
    :param number_of_images: The number of images to generate.
    :return: A list of generated images.
    """
    await app.generate_images(prompt, number_of_images)
    return app.generated_images


@cl.step(type="tool")
async def write_poem(prompt: str):
    """
    Generate a poem based on the given prompt.

    :param prompt: The prompt to generate the poem from.
    :return: The generated poem.
    """
    return await app.write_poem(prompt)

@cl.step(type="tool")
async def generate_image_prompt(prompt: str):
    """
    Generate an image prompt based on the given prompt.

    :param prompt: The prompt to generate the image prompt from.
    :return: The generated image prompt.
    """
    return await app.generate_image_prompt(prompt)


@cl.on_message
async def on_message_handler(message: cl.Message):
    """
    Handle incoming messages and generate appropriate responses.

    :param message: The incoming message.
    :return: None
    """
    stream_response = await app.send_message(message.content)
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
