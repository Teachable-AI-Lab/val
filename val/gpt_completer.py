import argparse
import hashlib
from openai import OpenAI
import os
import sys
# import torch

# openai_model = "gpt-4"
openai_model = "gpt-3.5-turbo"


class GPTCompleter:

    def __init__(self, openai_key):
        self.client = OpenAI(api_key=openai_key)
        self.cache = dict()

        if not os.path.exists('api_cache'):
            os.makedirs('api_cache')
        for fn in os.listdir('api_cache/'):
            with open('api_cache/%s' % fn, 'r') as f:
                self.cache[int(fn)] = f.read()

    def get_chat_gpt_completion(self, prompt, temp=0.0, rep_pen=0.0, max_length=256, stop=None):
        prompt_msgs = [x.strip() for x in prompt.split('***') if len(x.strip()) > 0]
        annotated_msgs = []
        role = 'user'
        other_role = 'assistant'
        for msg in prompt_msgs[::-1]:
            annotated_msgs = [{'role': role, 'content': msg.strip()}] + annotated_msgs
            (role, other_role) = (other_role, role)

        print('RAW MSGS:')
        print(annotated_msgs)

        if temp == 0:
            key = hash(('chat', prompt, rep_pen, max_length, stop))
            key = int(hashlib.md5(str(('chat', prompt, rep_pen, max_length, stop)).encode('utf-8')).hexdigest(), 16)
            if key not in self.cache:
                self.cache[key] = self.client.chat.completions.create(
                        model=openai_model,
                        messages=annotated_msgs,
                        max_tokens=max_length,
                        temperature=temp,
                        frequency_penalty=rep_pen,
                        stop=stop,
                        ).choices[0].message.content
                with open('api_cache/%d' % key, 'w') as f:
                    f.write(self.cache[key])
            print('RESP:')
            print(self.cache[key])
            return self.cache[key]
        else:
            res = self.client.chat.completions.create(
                    model=openai_model,
                    messages=annotated_msgs,
                    max_tokens=max_length,
                    temperature=temp,
                    frequency_penalty=rep_pen,
                    stop=stop,
                    ).choices[0].message.content
            print('RESP:')
            print(res)
            return res
