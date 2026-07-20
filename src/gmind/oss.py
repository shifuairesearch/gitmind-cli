from __future__ import annotations

import base64
import json


def upload_content(oss_auth: dict, file_guid: str, content: dict) -> str:
    import oss2

    auth = oss2.StsAuth(
        oss_auth["access_id"],
        oss_auth["access_secret"],
        oss_auth["security_token"],
    )
    bucket = oss2.Bucket(auth, oss_auth["endpoint"], oss_auth["bucket"])
    path_parts = oss_auth["path"]["resources"].split("/")[:3]
    upload_path = "/".join(path_parts) + f"/docs/{file_guid}.txt"
    callback_dict = {
        "callbackUrl": oss_auth["callback"]["callbackUrl"],
        "callbackBody": oss_auth["callback"]["callbackBody"],
        "callbackBodyType": "application/x-www-form-urlencoded",
    }
    headers = {
        "x-oss-callback": base64.b64encode(json.dumps(callback_dict).encode()).decode(),
        "Content-Type": "text/plain; charset=utf-8",
    }
    payload = json.dumps(content, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    result = bucket.put_object(upload_path, payload, headers=headers)
    if result.status != 200:
        raise RuntimeError(f"OSS upload failed: status {result.status}")
    response_body = result.resp.response.content.decode("utf-8")
    callback_data = json.loads(response_body)
    return callback_data["data"]["resource_id"]
