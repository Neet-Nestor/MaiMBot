#!/usr/bin/env python3
"""
Script to automatically fix model_config.toml to reduce 429 errors
Creates a backup before making changes
"""
import toml
import shutil
from datetime import datetime

def backup_config(config_path: str) -> str:
    """Create a backup of the config file"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{config_path}.backup_{timestamp}"
    shutil.copy2(config_path, backup_path)
    print(f"✓ Backup created: {backup_path}")
    return backup_path

def fix_config(config_path: str = "config/model_config.toml", dry_run: bool = False):
    """Fix configuration to reduce 429 errors"""
    
    print(f"{'='*60}")
    print(f"MaiBot 429 Error Configuration Fixer")
    print(f"{'='*60}\n")
    
    if dry_run:
        print("🔍 DRY RUN MODE - No changes will be made\n")
    
    # Load config
    try:
        with open(config_path, 'r') as f:
            config = toml.load(f)
    except Exception as e:
        print(f"✗ Failed to load config: {e}")
        return False
    
    changes_made = []
    
    # 1. Fix OpenAI provider settings
    print("[1/5] Checking API provider settings...")
    for provider in config.get('api_providers', []):
        if provider['name'] == 'OpenAI':
            old_retry = provider.get('retry_interval', 10)
            old_max_retry = provider.get('max_retry', 2)
            
            # Increase retry interval for 429 errors
            if provider.get('retry_interval', 10) < 30:
                provider['retry_interval'] = 60  # Wait full minute for rate limit reset
                changes_made.append(f"  • OpenAI retry_interval: {old_retry}s → 60s")
            
            # Increase max retries
            if provider.get('max_retry', 2) < 3:
                provider['max_retry'] = 3
                changes_made.append(f"  • OpenAI max_retry: {old_max_retry} → 3")
            
            print(f"  ✓ OpenAI provider updated")
    
    # 2. Swap model priorities - put DeepSeek first
    print("\n[2/5] Reordering model priorities...")
    task_configs = config.get('model_task_config', {})
    
    for task_name, task_config in task_configs.items():
        model_list = task_config.get('model_list', [])
        
        # Skip if no GPT models
        has_gpt = any('gpt' in m.lower() for m in model_list)
        has_deepseek = any('deepseek' in m.lower() for m in model_list)
        
        if has_gpt and has_deepseek:
            # Move DeepSeek to front
            deepseek_models = [m for m in model_list if 'deepseek' in m.lower()]
            other_models = [m for m in model_list if 'deepseek' not in m.lower()]
            
            new_list = deepseek_models + other_models
            if new_list != model_list:
                old_list = model_list.copy()
                task_config['model_list'] = new_list
                changes_made.append(f"  • {task_name}: {old_list} → {new_list}")
    
    if not any('model_list' in change for change in changes_made):
        print("  ✓ No reordering needed")
    
    # 3. Add fallback models where missing
    print("\n[3/5] Adding fallback models...")
    fallback_added = False
    
    for task_name, task_config in task_configs.items():
        model_list = task_config.get('model_list', [])
        
        # Add fallback for single-model configs
        if len(model_list) == 1:
            has_gpt = 'gpt' in model_list[0].lower()
            
            # For VLM, we can't easily add non-vision models
            if task_name == 'vlm':
                # Check if gpt-4o-mini-tts exists as a vision model
                changes_made.append(f"  ⚠️  {task_name} has only 1 model: {model_list[0]}")
                changes_made.append(f"      Consider adding another vision model manually")
            elif has_gpt:
                # Add deepseek-chat as fallback
                task_config['model_list'] = ['deepseek-chat'] + model_list
                changes_made.append(f"  • {task_name}: Added 'deepseek-chat' as primary")
                fallback_added = True
    
    if not fallback_added:
        print("  ✓ All configs have fallbacks")
    
    # 4. Check for exposed API keys
    print("\n[4/5] Checking for security issues...")
    security_issues = []
    for provider in config.get('api_providers', []):
        api_key = provider.get('api_key', '')
        if api_key and api_key not in ['your-api-key', 'your-google-api-key-1'] and len(api_key) > 20:
            if not api_key.startswith('sk-'):
                continue
            # OpenAI key detected
            provider['api_key'] = 'YOUR_OPENAI_API_KEY_HERE_PLEASE_REPLACE'
            security_issues.append(f"  ⚠️  {provider['name']} API key was exposed - replaced with placeholder")
            security_issues.append(f"      Original key: {api_key[:10]}...{api_key[-4:]}")
            security_issues.append(f"      → REGENERATE THIS KEY at platform.openai.com")
            security_issues.append(f"      → Then update config with new key")
    
    if security_issues:
        print("  ✗ Security issues found:")
        for issue in security_issues:
            print(issue)
            changes_made.append(issue)
    else:
        print("  ✓ No exposed API keys detected")
    
    # 5. Summary
    print(f"\n[5/5] Summary")
    print(f"{'='*60}")
    
    if changes_made:
        print(f"\n📝 Changes to be made ({len(changes_made)}):")
        for change in changes_made:
            print(change)
        
        if not dry_run:
            # Create backup
            backup_config(config_path)
            
            # Write changes
            try:
                with open(config_path, 'w') as f:
                    toml.dump(config, f)
                print(f"\n✓ Configuration updated successfully!")
                print(f"\n⚠️  ACTION REQUIRED:")
                print(f"  1. Update OpenAI API key in {config_path}")
                print(f"  2. Restart MaiBot for changes to take effect")
                return True
            except Exception as e:
                print(f"\n✗ Failed to write config: {e}")
                return False
        else:
            print(f"\n🔍 DRY RUN - No changes written")
            print(f"   Run without --dry-run to apply changes")
    else:
        print("✓ No changes needed - configuration looks good!")
    
    return True

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Fix MaiBot config to reduce 429 errors')
    parser.add_argument('--dry-run', action='store_true', help='Show changes without applying them')
    parser.add_argument('--config', default='config/model_config.toml', help='Path to config file')
    
    args = parser.parse_args()
    
    fix_config(args.config, dry_run=args.dry_run)

