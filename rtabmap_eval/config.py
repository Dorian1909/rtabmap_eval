"""Configuration loading and validation for RTAB-Map evaluation."""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


DEFAULT_CONFIG_PATH = Path(__file__).parent.parent / "configs" / "default.yaml"


def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge override into base (override wins on conflict)."""
    result = base.copy()
    for k, v in override.items():
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            result[k] = _deep_merge(result[k], v)
        else:
            result[k] = v
    return result


class Config:
    """Evaluation configuration, loaded from YAML with validation."""

    def __init__(self, data: Dict[str, Any]):
        self._data = data

    @classmethod
    def from_yaml(cls, path: Optional[Path] = None) -> "Config":
        """Load config from YAML file, falling back to defaults."""
        defaults = cls._load_yaml(DEFAULT_CONFIG_PATH)
        if path and path.exists():
            user = cls._load_yaml(path)
            merged = _deep_merge(defaults, user)
        else:
            merged = defaults
        cfg = cls(merged)
        cfg.validate()
        return cfg

    @staticmethod
    def _load_yaml(path: Path) -> dict:
        with open(path) as f:
            return yaml.safe_load(f) or {}

    def validate(self):
        """Validate required fields exist and paths make sense."""
        required_sections = ["rtabmap", "paths", "bag_mapping", "eval"]
        for section in required_sections:
            if section not in self._data:
                raise ValueError(f"Missing required config section: {section}")

        rtabmap = self._data["rtabmap"]
        for key in ["source_dir", "build_dir"]:
            if key not in rtabmap:
                raise ValueError(f"Missing rtabmap.{key} in config")

        paths = self._data["paths"]
        for key in ["bag_dir", "gt_dir", "launch_file", "record_script"]:
            if key not in paths:
                raise ValueError(f"Missing paths.{key} in config")

    # --- Convenience accessors ---

    @property
    def rtabmap_source(self) -> Path:
        return Path(self._data["rtabmap"]["source_dir"])

    @property
    def rtabmap_ros_source(self) -> Path:
        return Path(self._data["rtabmap"].get("ros_source_dir",
                   str(self.rtabmap_source / ".." / "catkin_ws" / "src" / "rtabmap")))

    @property
    def build_dir(self) -> Path:
        return Path(self._data["rtabmap"]["build_dir"])

    @property
    def db_path(self) -> Path:
        p = self._data["rtabmap"].get("db_path", "~/.ros/rtabmap.db")
        return Path(p).expanduser()

    @property
    def bag_dir(self) -> Path:
        return Path(self._data["paths"]["bag_dir"])

    @property
    def gt_dir(self) -> Path:
        return Path(self._data["paths"]["gt_dir"])

    @property
    def launch_file(self) -> Path:
        return Path(self._data["paths"]["launch_file"])

    @property
    def record_script(self) -> Path:
        return Path(self._data["paths"]["record_script"])

    @property
    def bag_mapping(self) -> Dict[str, str]:
        return self._data["bag_mapping"]

    @property
    def runs_per_bag(self) -> int:
        return int(self._data["eval"]["runs_per_bag"])

    @property
    def startup_wait(self) -> float:
        return float(self._data["eval"]["startup_wait_s"])

    @property
    def shutdown_wait(self) -> float:
        return float(self._data["eval"]["shutdown_wait_s"])

    @property
    def record_rate(self) -> float:
        return float(self._data["eval"]["record_rate_hz"])

    @property
    def playback_timeout(self) -> float:
        return float(self._data["eval"]["playback_timeout_s"])

    @property
    def evo_t_max_diff(self) -> float:
        return float(self._data.get("evo", {}).get("t_max_diff", 0.5))

    @property
    def evo_rpe_delta(self) -> int:
        return int(self._data.get("evo", {}).get("rpe_delta", 1))

    @property
    def evo_rpe_delta_unit(self) -> str:
        return str(self._data.get("evo", {}).get("rpe_delta_unit", "f"))

    @property
    def kill_patterns(self) -> List[str]:
        return self._data.get("kill_patterns", [])

    @property
    def env_overrides(self) -> Dict[str, str]:
        return self._data.get("env", {})

    def get_gt_file(self, bag_name: str) -> Optional[Path]:
        prefix = self.bag_mapping.get(bag_name)
        if not prefix:
            return None
        gt_file = self.gt_dir / f"{prefix}_gt.tum"
        return gt_file if gt_file.exists() else None

    def get_ros_source_cmd(self) -> str:
        """Return shell snippet to source ROS2 and the colcon workspace."""
        build = self.build_dir
        return (
            f"source /opt/ros/humble/setup.bash && "
            f"source {build}/install/setup.bash"
        )

    def to_dict(self) -> dict:
        return self._data.copy()
