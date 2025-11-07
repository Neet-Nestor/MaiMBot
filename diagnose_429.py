#!/usr/bin/env python3
"""
Diagnostic script to check OpenAI API rate limit status and configuration
"""
import os
import sys
import toml
import asyncio
from openai import AsyncOpenAI

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

async def check_openai_status(api_key: str, base_url: str):
    """Check OpenAI API status and rate limits"""
    print(f"\n{'='*60}")
    print("OpenAI API Configuration Check")
    print(f"{'='*60}")
    print(f"Base URL: {base_url}")
    print(f"API Key: {api_key[:10]}...{api_key[-4:]}")
    
    client = AsyncOpenAI(api_key=api_key, base_url=base_url)
    
    try:
        # Test with a minimal request
        print("\n[1/3] Testing API connectivity...")
        response = await client.chat.completions.create(
            model="gpt-4o-mini",  # Use cheapest model for testing
            messages=[{"role": "user", "content": "Hi"}],
            max_tokens=5
        )
        print("✓ API is accessible and working")
        print(f"  Response: {response.choices[0].message.content}")
        
        # Check rate limit headers from response
        print("\n[2/3] Checking rate limit information...")
        # Note: Rate limit info is in response headers but not directly accessible via SDK
        print("  Note: Rate limits depend on your OpenAI tier:")
        print("  - Free tier: Very limited (3 RPM for GPT-4, 500 RPM for GPT-3.5)")
        print("  - Tier 1: 500 RPM / 200K TPM")
        print("  - Tier 2: 5000 RPM / 2M TPM")
        print("  - Tier 3+: Higher limits")
        
        print("\n[3/3] Testing multiple rapid requests...")
        for i in range(3):
            try:
                await client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": f"Test {i}"}],
                    max_tokens=5
                )
                print(f"  Request {i+1}: ✓ Success")
                await asyncio.sleep(0.5)
            except Exception as e:
                print(f"  Request {i+1}: ✗ Failed - {e}")
                if "429" in str(e):
                    print("  → Rate limit hit! You need to:")
                    print("    1. Increase retry_interval in config")
                    print("    2. Reduce request frequency")
                    print("    3. Upgrade OpenAI tier")
                    print("    4. Use DeepSeek as primary model")
                break
        
        return True
        
    except Exception as e:
        print(f"✗ API check failed: {e}")
        if "401" in str(e):
            print("\n⚠️  Authentication Error:")
            print("  - Your API key is invalid or expired")
            print("  - Please update the API key in config/model_config.toml")
        elif "429" in str(e):
            print("\n⚠️  Rate Limit Error:")
            print("  - You've hit the rate limit before even starting")
            print("  - Your account may be in free tier with very low limits")
            print("  - Consider using DeepSeek as primary model")
        return False

def analyze_config():
    """Analyze current model configuration"""
    config_path = "config/model_config.toml"
    
    print(f"\n{'='*60}")
    print("Configuration Analysis")
    print(f"{'='*60}")
    
    try:
        with open(config_path, 'r') as f:
            config = toml.load(f)
        
        # Find OpenAI provider
        openai_provider = None
        for provider in config.get('api_providers', []):
            if provider['name'] == 'OpenAI':
                openai_provider = provider
                break
        
        if not openai_provider:
            print("✗ OpenAI provider not found in configuration")
            return None
        
        print(f"\nOpenAI Provider Settings:")
        print(f"  max_retry: {openai_provider.get('max_retry', 'not set')}")
        print(f"  retry_interval: {openai_provider.get('retry_interval', 'not set')} seconds")
        print(f"  timeout: {openai_provider.get('timeout', 'not set')} seconds")
        
        # Check which models use OpenAI
        gpt_models = [m for m in config.get('models', []) if m.get('api_provider') == 'OpenAI']
        print(f"\n{len(gpt_models)} GPT models configured:")
        for model in gpt_models:
            print(f"  - {model['name']} ({model['model_identifier']})")
        
        # Check task configs
        print(f"\nTask Configurations using GPT models:")
        task_configs = config.get('model_task_config', {})
        for task_name, task_config in task_configs.items():
            model_list = task_config.get('model_list', [])
            gpt_in_list = [m for m in model_list if any(gm['name'] == m for gm in gpt_models)]
            if gpt_in_list:
                print(f"  - {task_name}: {model_list}")
                if len(model_list) == 1:
                    print(f"    ⚠️  WARNING: Only 1 model, no fallback!")
                if model_list[0] in [gm['name'] for gm in gpt_models]:
                    print(f"    ⚠️  WARNING: GPT model is primary, will hit rate limits often!")
        
        return openai_provider
        
    except Exception as e:
        print(f"✗ Failed to analyze config: {e}")
        return None

def print_recommendations():
    """Print recommendations to fix 429 errors"""
    print(f"\n{'='*60}")
    print("RECOMMENDATIONS")
    print(f"{'='*60}")
    
    print("\n🔧 Immediate Fixes:")
    print("  1. INCREASE RETRY INTERVAL")
    print("     Change retry_interval from 10 to 60 seconds in OpenAI provider")
    print("     (Rate limits are per minute, so waiting 60s ensures you're in a new window)")
    
    print("\n  2. SWAP MODEL PRIORITY")
    print("     Put DeepSeek first in all model_lists that have GPT models")
    print("     Example: ['deepseek-chat', 'gpt-5-nano'] instead of ['gpt-5-nano', 'deepseek-chat']")
    
    print("\n  3. ADD FALLBACKS")
    print("     Ensure all task configs have at least 2 models")
    print("     VLM task only has ['gpt-5-mini'] - add a fallback!")
    
    print("\n  4. CHECK API KEY")
    print("     Your OpenAI API key is exposed in the config file")
    print("     - Regenerate it immediately at platform.openai.com")
    print("     - Consider using environment variables instead")
    
    print("\n💡 Long-term Solutions:")
    print("  • Upgrade OpenAI tier for higher rate limits")
    print("  • Use DeepSeek as primary (cheaper and faster)")
    print("  • Implement request queuing/throttling")
    print("  • Monitor usage with OpenAI dashboard")
    
    print("\n📊 Check your OpenAI tier at:")
    print("  https://platform.openai.com/settings/organization/limits")

async def main():
    print("""
╔══════════════════════════════════════════════════════════════╗
║        MaiBot GPT 429 Error Diagnostic Tool                 ║
╚══════════════════════════════════════════════════════════════╝
""")
    
    # Analyze configuration
    provider = analyze_config()
    
    # Check API status if config is valid
    if provider:
        await check_openai_status(
            provider['api_key'],
            provider['base_url']
        )
    
    # Print recommendations
    print_recommendations()
    
    print(f"\n{'='*60}")
    print("Diagnostic complete!")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    asyncio.run(main())

