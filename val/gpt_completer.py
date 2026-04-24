import argparse
import hashlib
from openai import OpenAI
import os
import sys
from typing import Union
# import torch

openai_model = "gpt-4"
AUTO_MODEL_VALUES = {"", "auto", "available", "latest"}


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
        self._use_model_autodiscovery = False

        if isinstance(openai_key, dict):
            api_key = openai_key.get("api_key")
            base_url = openai_key.get("base_url")
            model = openai_key.get("model")
            self._use_model_autodiscovery = self._is_auto_model(model)
            if model and not self._use_model_autodiscovery:
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
            if self._use_model_autodiscovery:
                self.model = self._select_available_model()

        if not os.path.exists('api_cache'):
            os.makedirs('api_cache')
        for fn in os.listdir('api_cache/'):
            with open('api_cache/%s' % fn, 'r') as f:
                self.cache[int(fn)] = f.read()

    def _is_auto_model(self, model) -> bool:
        if model is None:
            return True
        if not isinstance(model, str):
            return False
        return model.strip().lower() in AUTO_MODEL_VALUES

    def _list_available_models(self):
        response = self.client.models.list()
        models = getattr(response, "data", response)
        model_ids = []

        for model in models:
            model_id = getattr(model, "id", None)
            if not model_id and isinstance(model, dict):
                model_id = model.get("id")
            if model_id:
                model_ids.append(model_id)

        return model_ids

    def _select_available_model(self):
        model_ids = self._list_available_models()
        if not model_ids:
            raise RuntimeError("No models are available from the configured OpenAI-compatible endpoint.")

        selected_model = model_ids[0]
        print(f"Using available model from endpoint: {selected_model}")
        return selected_model

    def _looks_like_missing_model_error(self, exc: Exception) -> bool:
        msg = str(exc).lower()
        return (
            "model" in msg
            and (
                "not found" in msg
                or "does not exist" in msg
                or "not exist" in msg
                or "not available" in msg
                or "not served" in msg
            )
        )

    def _retry_with_available_model(self, request_kwargs, exc: Exception):
        if self._extra_body is None or not self._looks_like_missing_model_error(exc):
            raise exc

        previous_model = self.model
        self.model = self._select_available_model()
        request_kwargs["model"] = self.model
        print(f"Configured model unavailable ({previous_model}); retried with {self.model}.")
        return self.client.chat.completions.create(**request_kwargs)

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
        try:
            return self.client.chat.completions.create(**request_kwargs)
        except Exception as exc:
            return self._retry_with_available_model(request_kwargs, exc)

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
            key_model = self.model
            key = int(hashlib.md5(str(('chat', key_model, prompt, rep_pen, max_length, stop)).encode('utf-8')).hexdigest(), 16)
            if key not in self.cache:
                response = self._create_chat_completion(
                        annotated_msgs=annotated_msgs,
                        temp=temp,
                        rep_pen=rep_pen,
                        max_length=max_length,
                        stop=stop,
                        )
                if self.model != key_model:
                    key = int(hashlib.md5(str(('chat', self.model, prompt, rep_pen, max_length, stop)).encode('utf-8')).hexdigest(), 16)
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
