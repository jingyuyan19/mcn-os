import subprocess
import os
import json
import logging
import time

logger = logging.getLogger(__name__)

def execute_render(timeline_data, output_path):
    """
    Executes a Remotion render using the local CLI.
    
    Args:
        timeline_data (dict): The full JSON timeline for Remotion.
        output_path (str): Where to save the final MP4.
        
    Returns:
        bool: True if successful, False otherwise.
    """
    try:
        # 1. Save Timeline JSON to a temp file
        temp_json_path = output_path.replace('.mp4', '.json')
        with open(temp_json_path, 'w') as f:
            json.dump(timeline_data, f, indent=2)
            
        logger.info(f"🎬 Starting Remotion Render: {output_path}")
        logger.info(f"   Timeline: {temp_json_path}")

        # 2. Build the Command
        # nice -n 15: Low priority
        # npx ts-node render_cli.ts: The script we wrote
        cmd = [
            'nice', '-n', '15',
            'npx', 'ts-node', 'render_cli.ts',
            temp_json_path,
            output_path
        ]
        
        # 3. Execute
        # Robustly find 'rendering' dir relative to this file (middleware/lib/remotion_driver.py)
        # Expected: ../../rendering
        current_file_dir = os.path.dirname(os.path.abspath(__file__))
        rendering_dir = os.path.abspath(os.path.join(current_file_dir, "../../rendering"))
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=rendering_dir,
            text=True
        )
        
        # Stream logs
        stdout, stderr = process.communicate()
        
        if process.returncode != 0:
            logger.error(f"❌ Render Failed (Code {process.returncode})")
            logger.error(f"STDOUT: {stdout}")
            logger.error(f"STDERR: {stderr}")
            return False
            
        logger.info(f"✅ Render Complete!")
        return True

    except Exception as e:
        logger.error(f"❌ Render Exception: {e}")
        return False
