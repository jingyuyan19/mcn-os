#!/usr/bin/env python3
"""
LongCat Avatar Workflow Extender
Creates extended workflows by duplicating Extend groups for longer video generation.
"""

import json
import copy
import argparse
import sys

def duplicate_extend_group(data, num_additional_groups=5):
    """
    Duplicates the last Extend group to support longer videos.
    
    Args:
        data: The workflow JSON data
        num_additional_groups: Number of new Extend groups to add
    
    Returns:
        Modified workflow data
    """
    nodes = data.get("nodes", [])
    links = data.get("links", [])
    groups = data.get("groups", [])
    
    # Find Extend groups
    extend_groups = [g for g in groups if "Extend" in g.get("title", "")]
    if len(extend_groups) < 2:
        print("Error: Need at least 2 Extend groups to duplicate")
        return data
    
    # Get the last Extend group's bounding box
    last_group = extend_groups[-1]
    last_bbox = last_group.get("bounding", [0, 0, 1800, 1400])
    
    # Calculate spacing between groups
    second_last_group = extend_groups[-2]
    second_last_bbox = second_last_group.get("bounding", [0, 0, 1800, 1400])
    group_spacing = last_bbox[0] - second_last_bbox[0]
    
    print(f"Found {len(extend_groups)} Extend groups")
    print(f"Group spacing: {group_spacing:.0f} pixels")
    
    # Find nodes in the last Extend group
    x1, y1, w, h = last_bbox
    x2, y2 = x1 + w, y1 + h
    
    template_nodes = []
    for node in nodes:
        if isinstance(node, dict):
            pos = node.get("pos", [0, 0])
            nx = pos[0] if isinstance(pos, list) else pos.get("0", 0)
            ny = pos[1] if isinstance(pos, list) else pos.get("1", 0)
            if x1 <= nx <= x2 and y1 <= ny <= y2:
                template_nodes.append(node)
    
    print(f"Template group has {len(template_nodes)} nodes")
    
    # Get max IDs
    max_node_id = max(n.get("id", 0) for n in nodes if isinstance(n, dict)) + 1
    max_link_id = max(l[0] for l in links if isinstance(l, list) and len(l) > 0) + 1
    
    # Find links within the template group
    template_node_ids = {n.get("id") for n in template_nodes}
    template_links = []
    for link in links:
        if isinstance(link, list) and len(link) >= 6:
            from_node, to_node = link[1], link[3]
            if from_node in template_node_ids and to_node in template_node_ids:
                template_links.append(link)
    
    print(f"Template has {len(template_links)} internal links")
    
    # Create duplicates
    for i in range(num_additional_groups):
        x_offset = group_spacing * (i + 1)
        
        # Map old node IDs to new ones
        id_mapping = {}
        
        # Duplicate nodes
        for node in template_nodes:
            new_node = copy.deepcopy(node)
            old_id = node.get("id")
            new_id = max_node_id
            max_node_id += 1
            id_mapping[old_id] = new_id
            new_node["id"] = new_id
            
            # Update position
            pos = new_node.get("pos", [0, 0])
            if isinstance(pos, list):
                new_node["pos"] = [pos[0] + x_offset, pos[1]]
            else:
                new_node["pos"] = {"0": pos.get("0", 0) + x_offset, "1": pos.get("1", 0)}
            
            # Clear links (will be reconnected)
            for inp in new_node.get("inputs", []):
                inp["link"] = None
            for out in new_node.get("outputs", []):
                out["links"] = []
            
            nodes.append(new_node)
        
        # Duplicate internal links
        for link in template_links:
            old_link_id, old_from, from_slot, old_to, to_slot, link_type = link[:6]
            
            if old_from in id_mapping and old_to in id_mapping:
                new_link = [
                    max_link_id,
                    id_mapping[old_from],
                    from_slot,
                    id_mapping[old_to],
                    to_slot,
                    link_type
                ]
                max_link_id += 1
                links.append(new_link)
        
        # Add new group
        new_group = {
            "title": f"Extend_{i + len(extend_groups) + 1}",
            "bounding": [last_bbox[0] + x_offset, last_bbox[1], last_bbox[2], last_bbox[3]],
            "color": "#3f789e",
            "font_size": 24,
            "locked": False
        }
        groups.append(new_group)
        
        print(f"Added Extend group {i + len(extend_groups) + 1} at x={last_bbox[0] + x_offset:.0f}")
    
    data["nodes"] = nodes
    data["links"] = links
    data["groups"] = groups
    
    return data

def main():
    parser = argparse.ArgumentParser(description="Extend LongCat Avatar workflow for longer videos")
    parser.add_argument("input", help="Input workflow JSON file")
    parser.add_argument("output", help="Output workflow JSON file")
    parser.add_argument("-n", "--num-groups", type=int, default=5, 
                        help="Number of additional Extend groups (default: 5)")
    
    args = parser.parse_args()
    
    # Load workflow
    with open(args.input, "r") as f:
        data = json.load(f)
    
    print(f"Loaded workflow: {args.input}")
    
    # Extend the workflow
    extended_data = duplicate_extend_group(data, args.num_groups)
    
    # Calculate new duration
    original_groups = len([g for g in data.get("groups", []) if "Extend" in g.get("title", "")])
    new_groups = original_groups + args.num_groups
    duration = new_groups * 5.8
    
    print(f"\n=== Result ===")
    print(f"Total Extend groups: {new_groups}")
    print(f"Estimated max duration: {duration:.1f} seconds ({duration/60:.1f} minutes)")
    
    # Save
    with open(args.output, "w") as f:
        json.dump(extended_data, f, indent=2)
    
    print(f"\nSaved to: {args.output}")

if __name__ == "__main__":
    main()
