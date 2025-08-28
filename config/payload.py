import json
from datetime import datetime


def payload_genimage_2d(client_id: str, positive_prompt: str, width: int, height: int) -> dict:
    """
    Tạo payload cho ComfyUI API dựa trên client_id, positive_prompt, width và height.

    Args:
        client_id (str): ID của client
        positive_prompt (str): Prompt tích cực cho việc sinh ảnh
        width (int): Chiều rộng ảnh
        height (int): Chiều cao ảnh

    Returns:
        dict: Payload ComfyUI
    """
    return {

        "client_id": client_id,
        "prompt": {
            "1": {
                "inputs": {"samples": ["10", 0], "vae": ["4", 2]},
                "class_type": "VAEDecode",
                "_meta": {"title": "VAE Decode"}
            },
            "3": {
                "inputs": {"width": width, "height": height, "batch_size": 1},
                "class_type": "EmptyLatentImage",
                "_meta": {"title": "Empty Latent Image"}
            },
            "4": {
                "inputs": {"ckpt_name": "4T_2D.safetensors"},
                "class_type": "CheckpointLoaderSimple",
                "_meta": {"title": "Load Checkpoint"}
            },
            "10": {
                "inputs": {
                    "seed": int(datetime.now().timestamp()),
                    "steps": 20,
                    "cfg": 5,
                    "sampler_name": "euler_ancestral",
                    "scheduler": "normal",
                    "denoise": 1,
                    "model": ["18", 0],
                    "positive": ["15", 0],
                    "negative": ["16", 0],
                    "latent_image": ["3", 0]
                },
                "class_type": "KSampler",
                "_meta": {"title": "KSampler"}
            },
            "11": {
                "inputs": {
                    "text": "lowres, worst quality, low quality, bad anatomy, worst aesthetic, jpeg artifacts, scan artifacts, compression artifacts, old, early, bokeh, distorted anatomy, bad proportions, missing body part, missing limb, unclear eyes, bad hands, mutated hands, malformed hands, fused fingers, bad fingers, extra digits, fewer digits, missing fingers, extra arms, missing arm, malformed legs, malformed thighs, malformed feet, bad legs, bad thighs, bad feet, bad toes, fused toes, extra toes, missing toes, cross-eye, strabismus, lazy eye, open mouth",
                    "clip": ["18", 1]
                },
                "class_type": "CLIPTextEncode",
                "_meta": {"title": "CLIP Text Encode (Prompt)"}
            },
            "13": {
                "inputs": {
                    "text": positive_prompt,
                    "clip": ["18", 1]
                },
                "class_type": "CLIPTextEncode",
                "_meta": {"title": "CLIP Text Encode (Prompt)"}
            },
            "15": {
                "inputs": {"strength": 1, "conditioning": ["13", 0]},
                "class_type": "ConditioningSetAreaStrength",
                "_meta": {"title": "ConditioningSetAreaStrength"}
            },
            "16": {
                "inputs": {"strength": 1, "conditioning": ["11", 0]},
                "class_type": "ConditioningSetAreaStrength",
                "_meta": {"title": "ConditioningSetAreaStrength"}
            },
            "17": {
                "inputs": {
                    "filename_prefix": "ComfyUI",
                    "with_workflow": False,
                    "metadata_extra": json.dumps({
                        "Title": "Artwork by Ryn Wang",
                        "Description": "",
                        "Author": "Ryn Wang",
                        "Keywords": ["art", "digital", "creative"],
                        "Copyrights": "© 2025 Ryn Wang"
                    }),
                    "image": ["1", 0]
                },
                "class_type": "Save image with extra metadata [Crystools]",
                "_meta": {"title": "🪛 Save image with extra metadata"}
            },
            "18": {
                "inputs": {
                    "lora_name": "details_body.safetensors",
                    "strength_model": 0.8,
                    "strength_clip": 1,
                    "model": ["4", 0],
                    "clip": ["4", 1]
                },
                "class_type": "LoraLoader",
                "_meta": {"title": "Load LoRA"}
            }
        }
    }


def payload_genimage_Semi_Real(client_id: str, positive_prompt: str, width: int, height: int) -> dict:
    """
    Tạo payload cho ComfyUI API dựa trên client_id, positive_prompt, width và height.

    Args:
        client_id (str): ID của client
        positive_prompt (str): Prompt tích cực cho việc sinh ảnh
        width (int): Chiều rộng ảnh
        height (int): Chiều cao ảnh

    Returns:
        dict: Payload ComfyUI
    """
    return {

        "client_id": client_id,
        "prompt": {
            "1": {
                "inputs": {"samples": ["10", 0], "vae": ["4", 2]},
                "class_type": "VAEDecode",
                "_meta": {"title": "VAE Decode"}
            },
            "3": {
                "inputs": {"width": width, "height": height, "batch_size": 1},
                "class_type": "EmptyLatentImage",
                "_meta": {"title": "Empty Latent Image"}
            },
            "4": {
                "inputs": {"ckpt_name": "4T_Semi_Real.safetensors"},
                "class_type": "CheckpointLoaderSimple",
                "_meta": {"title": "Load Checkpoint"}
            },
            "10": {
                "inputs": {
                    "seed": int(datetime.now().timestamp()),
                    "steps": 20,
                    "cfg": 5,
                    "sampler_name": "euler",
                    "scheduler": "normal",
                    "denoise": 1,
                    "model": ["18", 0],
                    "positive": ["15", 0],
                    "negative": ["16", 0],
                    "latent_image": ["3", 0]
                },
                "class_type": "KSampler",
                "_meta": {"title": "KSampler"}
            },
            "11": {
                "inputs": {
                    "text": "lowres, worst quality, low quality, bad anatomy, worst aesthetic, jpeg artifacts, scan artifacts, compression artifacts, old, early, bokeh, distorted anatomy, bad proportions, missing body part, missing limb, unclear eyes, bad hands, mutated hands, malformed hands, fused fingers, bad fingers, extra digits, fewer digits, missing fingers, extra arms, missing arm, malformed legs, malformed thighs, malformed feet, bad legs, bad thighs, bad feet, bad toes, fused toes, extra toes, missing toes, cross-eye, strabismus, lazy eye, open mouth",
                    "clip": ["18", 1]
                },
                "class_type": "CLIPTextEncode",
                "_meta": {"title": "CLIP Text Encode (Prompt)"}
            },
            "13": {
                "inputs": {
                    "text": positive_prompt,
                    "clip": ["18", 1]
                },
                "class_type": "CLIPTextEncode",
                "_meta": {"title": "CLIP Text Encode (Prompt)"}
            },
            "15": {
                "inputs": {"strength": 1, "conditioning": ["13", 0]},
                "class_type": "ConditioningSetAreaStrength",
                "_meta": {"title": "ConditioningSetAreaStrength"}
            },
            "16": {
                "inputs": {"strength": 1, "conditioning": ["11", 0]},
                "class_type": "ConditioningSetAreaStrength",
                "_meta": {"title": "ConditioningSetAreaStrength"}
            },
            "17": {
                "inputs": {
                    "filename_prefix": "ComfyUI",
                    "with_workflow": False,
                    "metadata_extra": json.dumps({
                        "Title": "Artwork by Ryn Wang",
                        "Description": "",
                        "Author": "Ryn Wang",
                        "Keywords": ["art", "digital", "creative"],
                        "Copyrights": "© 2025 Ryn Wang"
                    }),
                    "image": ["1", 0]
                },
                "class_type": "Save image with extra metadata [Crystools]",
                "_meta": {"title": "🪛 Save image with extra metadata"}
            },
            "18": {
                "inputs": {
                    "lora_name": "details_body.safetensors",
                    "strength_model": 0.8,
                    "strength_clip": 1,
                    "model": ["4", 0],
                    "clip": ["4", 1]
                },
                "class_type": "LoraLoader",
                "_meta": {"title": "Load LoRA"}
            }
        }
    }


def payload_genimage_realistic(client_id: str, positive_prompt: str, width: int, height: int) -> dict:
    """
    Tạo payload cho ComfyUI API dựa trên client_id, positive_prompt, width và height.

    Args:
        client_id (str): ID của client
        positive_prompt (str): Prompt tích cực cho việc sinh ảnh
        width (int): Chiều rộng ảnh
        height (int): Chiều cao ảnh

    Returns:
        dict: Payload ComfyUI
    """
    return {
        "client_id": client_id,
        "prompt": {
            "5": {
                "inputs": {"width": width, "height": height, "batch_size": 1},
                "class_type": "EmptyLatentImage",
                "_meta": {"title": "Empty Latent Image"}
            },
            "6": {
                "inputs": {
                    "text": positive_prompt,
                    "clip": ["16", 1]
                },
                "class_type": "CLIPTextEncode",
                "_meta": {"title": "CLIP Text Encode (Prompt)"}
            },
            "7": {
                "inputs": {
                    "text": "lowres, worst quality, low quality, bad anatomy, worst aesthetic, jpeg artifacts, scan artifacts, compression artifacts, old, early, loli, child, bokeh, distorted anatomy, bad proportions, missing body part, missing limb, unclear eyes, bad hands, mutated hands, fused fingers, fewer digits, extra digits, extra arms, missing arm, missing leg, ai-generated, open mouth\n",
                    "clip": ["16", 1]
                },
                "class_type": "CLIPTextEncode",
                "_meta": {"title": "CLIP Text Encode (Prompt)"}
            },
            "11": {
                "inputs": {
                    "seed": int(datetime.now().timestamp()),
                    "steps": 40,
                    "cfg": 5,
                    "sampler_name": "dpmpp_3m_sde",
                    "scheduler": "karras",
                    "denoise": 1,
                    "model": ["39", 0],
                    "positive": ["35", 0],
                    "negative": ["36", 0],
                    "latent_image": ["5", 0]
                },
                "class_type": "KSampler",
                "_meta": {"title": "KSampler"}
            },
            "13": {
                "inputs": {"samples": ["11", 0], "vae": ["16", 2]},
                "class_type": "VAEDecode",
                "_meta": {"title": "VAE Decode"}
            },
            "16": {
                "inputs": {"ckpt_name": "4T_Realistic.safetensors"},
                "class_type": "CheckpointLoaderSimple",
                "_meta": {"title": "Load Checkpoint"}
            },
            "30": {
                "inputs": {
                    "filename_prefix": "ComfyUI",
                    "with_workflow": False,
                    "metadata_extra": json.dumps({
                        "Title": "Artwork by Ryn Wang",
                        "Description": "",
                        "Author": "Ryn Wang",
                        "Keywords": ["art", "digital", "creative"],
                        "Copyrights": "© 2025 Ryn Wang"
                    }),
                    "image": ["13", 0]
                },
                "class_type": "Save image with extra metadata [Crystools]",
                "_meta": {"title": "🪛 Save image with extra metadata"}
            },
            "35": {
                "inputs": {"strength": 1, "conditioning": ["6", 0]},
                "class_type": "ConditioningSetAreaStrength",
                "_meta": {"title": "ConditioningSetAreaStrength"}
            },
            "36": {
                "inputs": {"strength": 1, "conditioning": ["7", 0]},
                "class_type": "ConditioningSetAreaStrength",
                "_meta": {"title": "ConditioningSetAreaStrength"}
            },
            "39": {
                "inputs": {
                    "lora_name": "face.safetensors",
                    "strength_model": 1,
                    "model": ["16", 0]
                },
                "class_type": "LoraLoaderModelOnly",
                "_meta": {"title": "LoraLoaderModelOnly"}
            }
        }
    }
