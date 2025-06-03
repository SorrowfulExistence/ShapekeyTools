# Shapekey Tools

Blender addon with utilities for working with shape keys

Largely made according to my friend wosted's specifications

## Features

- **Select Affected Vertices** - Select vertices modified by active shape key (auto-switches to vertex edit mode)
- **Select Affected Faces** - Select faces containing modified vertices (auto-switches to face edit mode)
- **Blend from Vertex Group** - Use vertex group weights to control shape key influence
  - Invert option to reverse the vertex group influence
- **Clean Up Small Movements** - Remove unnecessary vertex data by resetting minimally-moved vertices to basis
  - Percentage mode: Clean bottom X% of moving vertices
  - Threshold mode: Clean all vertices moving less than specified distance
  - Can be used iteratively - each use recalculates based on remaining moving vertices

## Installation

1. Download the zip file, install through "add ons" section
2. Select the file and enable "Mesh: Shapekey Tools"

## Usage

1. Select a mesh with shape keys
2. Choose a shape key (not Basis)
3. Find tools in Properties > Mesh Data > Shape Keys > Shape Key Tools panel

### Cleanup Tool Tips

- Set your desired percentage before clicking "Clean Up Small Movements"
- Each click cleans that percentage of currently moving vertices
- Example: With 1000 moving vertices, 10% cleans 100. Next click cleans 10% of the remaining 900
- Info messages show how many vertices were cleaned and how many remain

## Requirements

- Blender 4.0+
- Mesh must have shape keys (lol)

The `_init_.py` file is the source code and the only file in the zip folder if you need easier access to it
