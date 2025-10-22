"""
天气查询Agent主程序
提供命令行界面和交互式对话功能
"""

import asyncio
import os
import sys
import logging
from typing import Optional
from pathlib import Path

import click
from dotenv import load_dotenv

from agent.weather_agent import WeatherAgent, create_weather_agent
from config.settings import Settings
from utils.logger import setup_logger

# 加载环境变量
load_dotenv()

# 设置日志
logger = setup_logger(__name__)


class WeatherCLI:
    """天气查询命令行界面"""
    
    def __init__(self):
        """初始化CLI"""
        self.agent: Optional[WeatherAgent] = None
        self.settings = Settings()
        
    async def initialize_agent(self) -> bool:
        """初始化Agent"""
        try:
            # 检查API密钥
            if not self.settings.deepseek_api_key:
                click.echo("❌ 错误: 未找到DEEPSEEK_API_KEY环境变量")
                click.echo("请在.env文件中设置您的DeepSeek API密钥")
                return False
            
            # MCP服务器命令
            server_command = ["python", "-m", "weather_mcp.server"]
            
            # 创建Agent
            click.echo("🚀 正在初始化天气查询Agent...")
            self.agent = await create_weather_agent(
                self.settings.deepseek_api_key,
                server_command
            )
            
            click.echo("✅ Agent初始化成功！")
            return True
            
        except Exception as e:
            click.echo(f"❌ Agent初始化失败: {e}")
            logger.error(f"Agent初始化失败: {e}")
            return False
    
    async def interactive_mode(self):
        """交互式对话模式"""
        click.echo("\n🌤️  欢迎使用智能天气查询助手！")
        click.echo("💡 您可以问我关于天气的任何问题，比如：")
        click.echo("   • 北京今天天气怎么样？")
        click.echo("   • 上海明天会下雨吗？")
        click.echo("   • 广州这周的天气预报")
        click.echo("   • 输入 'quit' 或 'exit' 退出\n")
        
        while True:
            try:
                # 获取用户输入
                user_input = click.prompt("🙋 您", type=str, prompt_suffix="").strip()
                
                # 检查退出命令
                if user_input.lower() in ['quit', 'exit', '退出', 'q']:
                    click.echo("👋 再见！感谢使用天气查询助手！")
                    break
                
                if not user_input:
                    continue
                
                # 显示处理中状态
                click.echo("🤔 正在思考中...")
                
                # 获取Agent响应
                response = await self.agent.chat(user_input)
                
                # 显示响应
                click.echo(f"🤖 助手: {response}\n")
                
            except KeyboardInterrupt:
                click.echo("\n👋 再见！感谢使用天气查询助手！")
                break
            except Exception as e:
                click.echo(f"❌ 处理请求时出错: {e}")
                logger.error(f"交互模式错误: {e}")
    
    async def single_query(self, query: str):
        """单次查询模式"""
        try:
            click.echo(f"🙋 查询: {query}")
            click.echo("🤔 正在查询中...")
            
            response = await self.agent.chat(query)
            click.echo(f"🤖 回答: {response}")
            
        except Exception as e:
            click.echo(f"❌ 查询失败: {e}")
            logger.error(f"单次查询错误: {e}")
    
    async def cleanup(self):
        """清理资源"""
        if self.agent:
            await self.agent.close()


# CLI命令定义
@click.group()
@click.version_option(version="1.0.0", prog_name="天气查询Agent")
def cli():
    """🌤️ 智能天气查询助手
    
    基于DeepSeek模型和高德地图API的智能天气查询工具
    """
    pass


@cli.command()
@click.option('--query', '-q', help='要查询的天气问题')
@click.option('--interactive', '-i', is_flag=True, help='启动交互式模式')
@click.option('--debug', is_flag=True, help='启用调试模式')
def chat(query: Optional[str], interactive: bool, debug: bool):
    """开始天气查询对话"""
    
    # 设置日志级别
    if debug:
        logging.getLogger().setLevel(logging.DEBUG)
        click.echo("🔍 调试模式已启用")
    
    async def run_chat():
        cli_app = WeatherCLI()
        
        try:
            # 初始化Agent
            if not await cli_app.initialize_agent():
                sys.exit(1)
            
            # 根据参数选择模式
            if query:
                # 单次查询模式
                await cli_app.single_query(query)
            elif interactive or not query:
                # 交互式模式
                await cli_app.interactive_mode()
            
        except KeyboardInterrupt:
            click.echo("\n👋 程序已中断")
        except Exception as e:
            click.echo(f"❌ 程序运行错误: {e}")
            logger.error(f"程序运行错误: {e}")
            sys.exit(1)
        finally:
            await cli_app.cleanup()
    
    # 运行异步函数
    asyncio.run(run_chat())


@cli.command()
def config():
    """显示配置信息"""
    settings = Settings()
    
    click.echo("📋 当前配置:")
    click.echo(f"   • 高德地图API密钥: {'已设置' if settings.amap_api_key else '❌ 未设置'}")
    click.echo(f"   • DeepSeek API密钥: {'已设置' if settings.deepseek_api_key else '❌ 未设置'}")
    click.echo(f"   • 日志级别: {settings.log_level}")
    click.echo(f"   • 缓存过期时间: {settings.cache_expire_minutes}分钟")
    click.echo(f"   • API请求超时: {settings.api_timeout}秒")


@cli.command()
def test():
    """运行系统测试"""
    
    async def run_tests():
        click.echo("🧪 开始系统测试...")
        
        cli_app = WeatherCLI()
        
        try:
            # 测试Agent初始化
            click.echo("1. 测试Agent初始化...")
            if not await cli_app.initialize_agent():
                click.echo("❌ Agent初始化测试失败")
                return
            click.echo("✅ Agent初始化测试通过")
            
            # 测试基本查询
            click.echo("2. 测试基本天气查询...")
            test_queries = [
                "北京今天天气",
                "上海天气预报",
                "广州温度"
            ]
            
            for i, query in enumerate(test_queries, 1):
                try:
                    click.echo(f"   测试 {i}: {query}")
                    response = await cli_app.agent.chat(query)
                    if response and len(response) > 10:
                        click.echo(f"   ✅ 测试 {i} 通过")
                    else:
                        click.echo(f"   ❌ 测试 {i} 失败: 响应过短")
                except Exception as e:
                    click.echo(f"   ❌ 测试 {i} 失败: {e}")
            
            click.echo("🎉 系统测试完成！")
            
        except Exception as e:
            click.echo(f"❌ 测试过程中出错: {e}")
        finally:
            await cli_app.cleanup()
    
    asyncio.run(run_tests())


@cli.command()
@click.argument('question', required=True)
@click.option('--debug', is_flag=True, help='启用调试模式')
def query(question: str, debug: bool):
    """快速查询天气信息"""
    
    # 设置日志级别
    if debug:
        logging.getLogger().setLevel(logging.DEBUG)
        click.echo("🔍 调试模式已启用")
    
    async def run_query():
        cli_app = WeatherCLI()
        
        try:
            # 初始化Agent
            if not await cli_app.initialize_agent():
                sys.exit(1)
            
            # 执行查询
            await cli_app.single_query(question)
            
        except KeyboardInterrupt:
            click.echo("\n👋 程序已中断")
        except Exception as e:
            click.echo(f"❌ 程序运行错误: {e}")
            logger.error(f"程序运行错误: {e}")
            sys.exit(1)
        finally:
            await cli_app.cleanup()
    
    # 运行异步函数
    asyncio.run(run_query())


@cli.command()
@click.argument('city', required=True)
def search(city: str):
    """搜索城市信息"""
    
    async def run_search():
        cli_app = WeatherCLI()
        
        try:
            # 初始化Agent
            if not await cli_app.initialize_agent():
                sys.exit(1)
            
            # 执行城市搜索
            click.echo(f"🔍 搜索城市: {city}")
            response = await cli_app.agent.chat(f"搜索城市 {city}")
            click.echo(f"🏙️ 搜索结果: {response}")
            
        except KeyboardInterrupt:
            click.echo("\n👋 程序已中断")
        except Exception as e:
            click.echo(f"❌ 搜索失败: {e}")
            logger.error(f"城市搜索错误: {e}")
            sys.exit(1)
        finally:
            await cli_app.cleanup()
    
    # 运行异步函数
    asyncio.run(run_search())


@cli.command()
def setup():
    """设置向导"""
    click.echo("🛠️  天气查询Agent设置向导\n")
    
    # 检查.env文件
    env_file = Path(".env")
    if not env_file.exists():
        click.echo("创建.env配置文件...")
        env_file.write_text(Path(".env.example").read_text())
        click.echo("✅ 已创建.env文件")
    
    # 检查API密钥
    settings = Settings()
    
    if not settings.amap_api_key:
        click.echo("❌ 未找到高德地图API密钥")
        click.echo("请在.env文件中设置AMAP_API_KEY")
    else:
        click.echo("✅ 高德地图API密钥已设置")
    
    if not settings.deepseek_api_key:
        click.echo("❌ 未找到DeepSeek API密钥")
        click.echo("请在.env文件中设置DEEPSEEK_API_KEY")
        click.echo("获取地址: https://platform.deepseek.com/api_keys")
    else:
        click.echo("✅ DeepSeek API密钥已设置")
    
    # 检查依赖
    click.echo("\n📦 检查依赖...")
    try:
        import langgraph
        import langchain_openai
        import mcp
        click.echo("✅ 核心依赖已安装")
    except ImportError as e:
        click.echo(f"❌ 缺少依赖: {e}")
        click.echo("请运行: pip install -r requirements.txt")
    
    click.echo("\n🎉 设置检查完成！")
    click.echo("如果所有项目都显示✅，您可以运行: python main.py chat")


def main():
    """主函数"""
    try:
        cli()
    except Exception as e:
        click.echo(f"❌ 程序启动失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()