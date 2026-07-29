import os
from glob import glob
from setuptools import setup

package_name = 'rtabmap_eval'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', glob('launch/*.launch.py')),
        ('share/' + package_name + '/configs', glob('configs/*.yaml')),
    ],
    install_requires=[
        'setuptools',
        'evo>=1.30.0',
        'pyyaml',
    ],
    python_requires='>=3.8',
    zip_safe=True,
    author='you',
    author_email='you@example.com',
    maintainer='you',
    maintainer_email='you@example.com',
    keywords=['ROS2', 'SLAM', 'RTAB-Map', 'evaluation'],
    classifiers=[
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Topic :: Software Development',
    ],
    description='RTAB-Map evaluation platform: benchmark SLAM trajectories with APE/RPE.',
    license='MIT',
    entry_points={
        'console_scripts': [
            'rtabmap-eval=rtabmap_eval.__main__:main',
            'record_tf_trajectory=rtabmap_eval.record_tf_trajectory:main',
            'nv12_to_bgr=rtabmap_eval.nv12_to_bgr:main',
            'odom_to_tf=rtabmap_eval.odom_to_tf:main',
        ],
    },
)
