import os
import yaml

def init_prompt_map():
    # Path to the YAML file
    yaml_file_path = os.path.join(
        os.path.dirname(__file__), "ai_prompts.yaml"
    )

    with open(yaml_file_path, 'r', encoding='utf-8') as file:    
        prompts_map = yaml.safe_load(file)
    
    return prompts_map
    