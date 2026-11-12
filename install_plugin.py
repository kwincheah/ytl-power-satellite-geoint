#!/usr/bin/env python3
"""One-click installer for Satellite GEOINT & Earth Observation Plugin for Apex Vision Studio."""

import os
import sys
import shutil
from pathlib import Path


def install_plugin():
    script_dir = Path(__file__).resolve().parent
    source_plugin_dir = script_dir / "plugins" / "geoint_satellite_plugin"
    if not source_plugin_dir.exists():
        # Maybe executed from inside plugins/geoint_satellite_plugin/
        if (script_dir / "plugin.json").exists():
            source_plugin_dir = script_dir
        else:
            print(f"[ERROR] Could not find geoint_satellite_plugin source directory.")
            sys.exit(1)

    # 1. User profile directory ~/.apex_vision/plugins/
    home_plugins = Path.home() / ".apex_vision" / "plugins"
    target_home = home_plugins / "geoint_satellite_plugin"

    print(f"[*] Installing plugin to user profile: {target_home}")
    home_plugins.mkdir(parents=True, exist_ok=True)
    if target_home.exists():
        shutil.rmtree(target_home)
    shutil.copytree(source_plugin_dir, target_home)
    print(f"[OK] Installed to user profile: {target_home}")

    # 2. Check for local Apex Vision Studio repositories nearby
    potential_repos = [
        script_dir.parent / "VMClone",
        script_dir.parent / "vision-studio",
        Path("C:/Users/winch/Downloads/VMClone"),
    ]

    for repo in potential_repos:
        if repo.exists() and (repo / "apex_vision").exists():
            repo_plugin_dir = repo / "plugins" / "geoint_satellite_plugin"
            repo_projects_dir = repo / "projects"
            print(f"[*] Found Apex Vision Studio repo at: {repo}")
            
            repo_plugin_dir.parent.mkdir(parents=True, exist_ok=True)
            if repo_plugin_dir.exists():
                shutil.rmtree(repo_plugin_dir)
            shutil.copytree(source_plugin_dir, repo_plugin_dir)
            print(f"[OK] Installed to {repo_plugin_dir}")

            # Also copy workflow project if present
            flow_src = script_dir / "projects" / "YTL_Solar_Inspection.apex"
            if flow_src.exists():
                repo_projects_dir.mkdir(parents=True, exist_ok=True)
                flow_dst = repo_projects_dir / "YTL_Solar_Inspection.apex"
                shutil.copy2(flow_src, flow_dst)
                print(f"[OK] Installed workflow project to {flow_dst}")

    print("\n=======================================================")
    print(" Satellite GEOINT Plugin Successfully Installed!")
    print("=======================================================")
    print("Included Tools:")
    print("  1. Satellite STAC Source (STACSatelliteSourceTool)")
    print("  2. Spectral Index & HSV Filter (SpectralIndexFilterTool)")
    print("  3. Geospatial Area & Capacity Estimator (GeospatialAreaCapacityTool)")
    print("  4. Consensus Variance & Delivery Branch (ConsensusVarianceBranchTool)")
    print("Workflow: projects/YTL_Solar_Inspection.apex")
    print("=======================================================\n")


if __name__ == "__main__":
    install_plugin()
