from litellm import completion
import os


os.environ['DEEPSEEK_API_KEY'] = ""
response = completion(
    model="deepseek/deepseek-chat",
    messages=[
       {"role": "user", "content": "hello from litellm"}
   ],
)
print(response.choices[0].message.content)

