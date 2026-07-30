"""Configuration loading and validation for RTAB-Map evaluation."""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


def _find_default_config() -> Path:
    """Locate configs/default.yaml.

    Prefers the colcon-installed share directory; falls back to the
    source tree (editable install / running from repo).
    """
    try:
        from ament_index_python.packages import get_package_share_directory
        share = Path(get_package_share_directory('rtabmap_eval'))
        candidate = share / 'configs' / 'default.yaml'
        if candidate.exists():
            return candidate
    except Exception:
        pass
    return Path(__file__).parent.parent / "configs" / "default.yaml"


DEFAULT_CONFIG_PATH = _find_default_config()


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

    _REPO_ROOT = Path(__file__).parent.parent  # rtabmap_eval/

    def __init__(self, data: Dict[str, Any]):
        self._data = data

    @property
    def _repo_root(self) -> Path:
        return self._REPO_ROOT

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
        required_sections = ["paths", "bag_mapping", "eval"]
        for section in required_sections:
            if section not in self._data:
                raise ValueError(f"Missing required config section: {section}")

        paths = self._data["paths"]
        for key in ["bag_dir", "gt_dir", "launch_cmd"]:
            if key not in paths:
                raise ValueError(f"Missing paths.{key} in config")
        if str(paths["launch_cmd"]).strip() in ("", "REPLACE_ME"):
            raise ValueError(
                "paths.launch_cmd must be set to a real launch command "
                "(e.g. 'ros2 launch /abs/path/to/your.launch.py') in user.yaml")

    # --- Convenience accessors ---

    @property
    def db_path(self) -> Path:
        p = self._data.get("db_path", "~/.ros/rtabmap.db")
        return Path(p).expanduser()

    @property
    def bag_dir(self) -> Path:
        return Path(self._data["paths"]["bag_dir"])

    @property
    def gt_dir(self) -> Path:
        return Path(self._data["paths"]["gt_dir"])

    @property
    def launch_cmd(self) -> str:
        return str(self._data["paths"]["launch_cmd"])

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
    def validity_min_poses(self) -> int:
        return int(self._data.get("eval", {}).get("validity", {}).get("min_poses", 10))

    @property
    def validity_min_coverage(self) -> float:
        return float(self._data.get("eval", {}).get("validity", {}).get("min_coverage", 0.5))

    @property
    def validity_min_extent_m(self) -> float:
        return float(self._data.get("eval", {}).get("validity", {}).get("min_extent_m", 0.05))

    @property
    def validity_span_tolerance_s(self) -> float:
        return float(self._data.get("eval", {}).get("validity", {}).get("span_tolerance_s", 2.0))

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
    def env_overrides(self) -> Dict[str, str]:
        return self._data.get("env", {})

    def eval_launch_args(self) -> Dict[str, str]:
        """Flatten eval_launch section into a dict of launch arguments.

        Nested `static_tf` is flattened as `static_tf_<key>`.
        Used by runner to append `key:=value` pairs to the eval launch command.
        """
        section = self._data.get("eval_launch", {}) or {}
        args: Dict[str, str] = {}
        for k, v in section.items():
            if isinstance(v, dict):
                for sub_k, sub_v in v.items():
                    args[f"{k}_{sub_k}"] = str(sub_v)
            else:
                if isinstance(v, bool):
                    args[k] = "true" if v else "false"
                else:
                    args[k] = str(v)
        return args

    def get_gt_file(self, bag_name: str) -> Optional[Path]:
        prefix = self.bag_mapping.get(bag_name)
        if not prefix:
            return None
        gt_file = self.gt_dir / f"{prefix}_gt.tum"
        return gt_file if gt_file.exists() else None

    def to_dict(self) -> dict:
        return self._data.copy()
