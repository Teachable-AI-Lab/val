import argparse
import hashlib
from openai import OpenAI
import os
import sys
from typing import Union
# import torch

openai_model = "gpt-4"


def _is_official_openai_base_url(base_url: str) -> bool:
    if not base_url:
        return True
    return "api.openai.com" in base_url.lower()


class GPTCompleter:

    def __init__(self, openai_key: Union[str, dict]):
        # Accept either a raw API key string (legacy) or a config dict:
        # {"api_key": "...", "base_url": "...", "model": "..."}.
        self.model = openai_model
        client_kwargs = {}
        base_url = None

        if isinstance(openai_key, dict):
            api_key = openai_key.get("api_key")
            base_url = openai_key.get("base_url")
            model = openai_key.get("model")
            if model:
                self.model = model
            client_kwargs["api_key"] = api_key
            if base_url:
                client_kwargs["base_url"] = base_url
        else:
            client_kwargs["api_key"] = openai_key

        self.client = OpenAI(**client_kwargs)
        self.cache = dict()
        # Some OpenAI-compatible backends (e.g. Qwen on vLLM) return
        # reasoning tokens unless explicitly disabled. Official OpenAI
        # endpoints should not receive these backend-specific parameters.
        self._extra_body = None
        if base_url and not _is_official_openai_base_url(base_url):
            self._extra_body = {"chat_template_kwargs": {"enable_thinking": False}}

        if not os.path.exists('api_cache'):
            os.makedirs('api_cache')
        for fn in os.listdir('api_cache/'):
            with open('api_cache/%s' % fn, 'r') as f:
                self.cache[int(fn)] = f.read()

    def _create_chat_completion(self, annotated_msgs, temp, rep_pen, max_length, stop):
        request_kwargs = {
            "model": self.model,
            "messages": annotated_msgs,
            "max_tokens": max_length,
            "temperature": temp,
            "frequency_penalty": rep_pen,
            "stop": stop,
        }
        if self._extra_body is not None:
            request_kwargs["extra_body"] = self._extra_body
        return self.client.chat.completions.create(**request_kwargs)

    def get_chat_gpt_completion(self, prompt, temp=0.0, rep_pen=0.0, max_length=256, stop=None):
        prompt_msgs = [x.strip() for x in prompt.split('***') if len(x.strip()) > 0]
        annotated_msgs = []
        role = 'user'
        other_role = 'assistant'
        for msg in prompt_msgs[::-1]:
            annotated_msgs = [{'role': role, 'content': msg.strip()}] + annotated_msgs
            (role, other_role) = (other_role, role)

        # print('RAW MSGS:')
        # print(annotated_msgs)

        if temp == 0:
            key = hash(('chat', prompt, rep_pen, max_length, stop))
            key = int(hashlib.md5(str(('chat', prompt, rep_pen, max_length, stop)).encode('utf-8')).hexdigest(), 16)
            if key not in self.cache:
                response = self._create_chat_completion(
                        annotated_msgs=annotated_msgs,
                        temp=temp,
                        rep_pen=rep_pen,
                        max_length=max_length,
                        stop=stop,
                        )
                self.cache[key] = self._extract_text(response)
                with open('api_cache/%d' % key, 'w') as f:
                    f.write(self.cache[key])
            # print('RESP:')
            # print(self.cache[key])
            return self.cache[key]
        else:
            response = self._create_chat_completion(
                    annotated_msgs=annotated_msgs,
                    temp=temp,
                    rep_pen=rep_pen,
                    max_length=max_length,
                    stop=stop,
                    )
            res = self._extract_text(response)
            # print('RESP:')
            # print(res)
            return res

    def _extract_text(self, response) -> str:
        """
        Robustly extract assistant text from OpenAI-compatible responses.
        """
        if not response or not response.choices:
            return ""

        msg = response.choices[0].message
        content = getattr(msg, "content", None)
        if content is not None:
            return content

        # Fallback for reasoning-style responses.
        reasoning = getattr(msg, "reasoning", None)
        if reasoning is not None:
            return reasoning

        return ""
