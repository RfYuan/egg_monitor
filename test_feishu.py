import requests
import json
from dotenv import load_dotenv
import os

load_dotenv()

FEISHU_WEBHOOK_URL = os.getenv("FEISHU_WEBHOOK_URL")

def test_feishu_connection():
    if not FEISHU_WEBHOOK_URL:
        print("❌ 错误：FEISHU_WEBHOOK_URL 未配置")
        return False
    
    print(f"📡 测试飞书 Webhook: {FEISHU_WEBHOOK_URL[:50]}...")
    
    payload = {
        "msg_type": "text",
        "content": {
            "text": "✅ 飞书机器人连接测试成功！\n\n鸡蛋期货监控系统即将上线..."
        }
    }
    
    try:
        response = requests.post(
            FEISHU_WEBHOOK_URL,
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        response.raise_for_status()
        result = response.json()
        
        if result.get("code") == 0:
            print("✅ 飞书消息发送成功！")
            print(f"📝 响应: {result}")
            return True
        else:
            print(f"❌ 飞书消息发送失败: {result}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ 请求异常: {e}")
        return False
    except json.JSONDecodeError as e:
        print(f"❌ 响应解析失败: {e}")
        return False

if __name__ == "__main__":
    test_feishu_connection()
