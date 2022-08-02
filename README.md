<div align="center" markdown>

<img src="https://user-images.githubusercontent.com/48245050/182337681-9c123361-3a18-4ceb-9d4e-be170479b4c3.png"/>

# Create Trainset for SmartTool 

<p align="center">

  <a href="#Overview">Overview</a> •
  <a href="#How-To-Run">How To Run</a>
</p>

[![](https://img.shields.io/badge/slack-chat-green.svg?logo=slack)](https://supervise.ly/slack)
![GitHub release (latest SemVer)](https://img.shields.io/github/v/release/supervisely-ecosystem/create-trainset-for-smarttool)
[![views](https://app.supervise.ly/img/badges/views/supervisely-ecosystem/create-trainset-for-smarttool)](https://supervise.ly)
[![runs](https://app.supervise.ly/img/badges/runs/supervisely-ecosystem/create-trainset-for-smarttool)](https://supervise.ly)

</div>

## Overview

This app created training dataset for SmartTool from labeled project. All classes in the input project have to be `Bitmaps`. Please, use app [Rasterize objects on images](https://github.com/supervisely-ecosystem/rasterize-objects-on-images) to raster all objects and prepare correct object masks. It is crucial for this app.  

All classes will be converted to a single class, then instances crop will be performed and then positive/negative points will be randomly generated. 

**Note**: Customization of SmartTool is available only in Enterprise Edition (EE).

## How To Run

### Step 1: Run from context menu of project

Go to "Context Menu" of project with images -> "Run App" -> "Training data" -> "Create Trainset for SmartTool"

<img src="https://i.imgur.com/0uTRa3V.png" width="600"/>

### Step 2:  Waiting until the app is started
Once app is started, new task appear in workspace tasks. Wait message `Application is started ...` (1) and then press `Open` button (2).

<img src="https://i.imgur.com/C6zo9Q2.png"/>

### Step 3: Define augmentations

On the left side you will see the augmentation options. You can keep the default settings. You can press `Preview` button to see the augmentations applied to a random image. Press `Run` button to start the augmentation process. As a result new project will be created. Once all augmentations are applied, the app will be stopped automatically. 


<img src="https://i.imgur.com/t5HZgXf.png"/>

