import dashscope
import sys
from dashscope import Generation

# 强烈建议通过环境变量配置密钥
dashscope.api_key = "sk-624c20dbecac4a41913f1e66e83ea1ec"  # 替换为真实密钥

def get_qwen_response(prompt):
    try:
        response = Generation.call(
            model="qwen-turbo",
            messages=[
                {"role": "system", "content": "你是一个专业的Linux终端助手"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )

        # 增加响应有效性检查
        if not response or not hasattr(response, 'output'):
            raise ValueError("无效的API响应结构")

        if response.status_code != 200:
            raise ConnectionError(f"API请求失败，状态码：{response.status_code}")

        # 调试时可打印完整响应
        print("完整响应:", response)
        # 新版API结构解析
        if response and hasattr(response, 'output'):
            if 'text' in response.output:  # 检查text字段
                return response.output.text.strip()
            else:
                raise ValueError("响应缺少text字段")
        else:
            raise ConnectionError("API未返回有效响应")

        ##return response.output.choices[0]['message']['content']

    except Exception as e:
        return f"⚠️ 服务异常: {str(e)}"

if __name__ == "__main__":
    try:
        user_input = " ".join(sys.argv[1:])
        if not user_input:
            raise ValueError("请输入查询内容")

        result = get_qwen_response(user_input)
        print(f"🔍 通义千问回复：\n{result}")

    except Exception as e:
        print(f"❌ 严重错误: {str(e)}")
        # 打印堆栈跟踪（调试时取消注释）
        import traceback
        traceback.print_exc()
