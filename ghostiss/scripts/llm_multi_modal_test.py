import base64
from openai import OpenAI

from PIL import Image


def encode_image(image_path, convert=False):
    final_path = image_path

    if convert:
        img_png = Image.open(image_path)
        final_path = 'tmp.jpeg'
        img_png.save(final_path)

    with open(final_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')


client = OpenAI(
    base_url = 'http://localhost:11434/v1',
    api_key = 'ollama',  # required, but unused
)

base64_image = encode_image("/home/llm/Downloads/github-img-8.png")

response = client.chat.completions.create(
    model = "llava-llama3:8b-v1.1-fp16",
    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "extract text from img and notice keep indent and newline (must don't lack '\n')"
                },
                {
                  "type": "image_url",
                  "image_url": {
                    "url": f"data:image/jpeg;base64,{base64_image}",
                  },
                }
            ],
        }
    ]
)

print(response.choices[0].message.content)


# import anthropic
#
# client = anthropic.Anthropic(
#     # defaults to os.environ.get("ANTHROPIC_API_KEY")
#     # todo del when upload
#     api_key="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",
# )
# message = client.messages.create(
#     model="claude-3-5-sonnet-20240620",
#     max_tokens=1024,
#     messages=[
#         {"role": "user", "content": "Hello, Claude"}
#     ]
# )
# print(message.content)
#




