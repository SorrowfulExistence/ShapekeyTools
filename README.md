# Shapekey Tools

Blender addon with some niche utilities for working with shape keys

Largely made according to my friend wosted's specifications

## Features

- **Select Affected Vertices** - Select vertices modified by active shape key
- **Select Affected Faces** - Select faces containing modified vertices  
- **Blend from Vertex Group** - Use vertex group weights to control shape key influence
- **Blend to Basis by Distance** - Blend vertices back to basis based on displacement

## Installation

1. Download `__init__.py`
2. In Blender: Edit > Preferences > Add-ons > Install
3. Select the file and enable "Mesh: Shapekey Tools"

## Usage

1. Select a mesh with shape keys
2. Choose a shape key (not Basis)
3. Find tools in Properties > Mesh Data > Shape Keys > Shape Key Tools panel

## Requirements

- Blender 4.0+
- Mesh must have shape keys (lol)

