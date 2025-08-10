# USD-Python-API-Usage-Demo
A minimal Python project demonstrating how to write and compose Pixar USD (.usd/.usda) scenes using the USD Python API. You can clone this repo, install dependencies, and run the scripts to verify reading, writing, and simple layer‐composition.


---

## Prerequisites

- Python 3.6 or later  
- Pixar’s USD Python bindings (the `pxr` module) installed and on your `PYTHONPATH`  
- A terminal or command prompt with access to the USD tools and scripts  

---

## Getting Started

1. Clone this repository to your local machine:  

   ```bash
   git clone https://github.com/EricLalumiere/USD-Python-API-Usage-Demo.git
   ```

---

## Project Layout

- **USD-Python-API-Usage-Demo/** — Main directory containing the composer scripts and sample scenes
- **scenes/scene_cube.usda** — Sample USD scene containing a cube
- **scenes/scene_Hero.usda** — Sample USD more complex scene containing a "hero" character
- **scenes/scene_spere.usda** — Sample USD scene containing a sphere
- **scenes/scene_Villain.usda** — Sample USD more complex scene containing a "villain" character
- **write_random_scene.py** — Script to generate a random USD scene with a cube and sphere
- **scripts/simple_composer.py** — Script to merge two USD scenes into one  
- **scripts/validate_composed.py** — Script to validate the merged scene against the sources  
- **README.md** — This guide  

---

## Usage
  
### 1. Writing a random USD scene
Run `write_random_scene.py` to create a random USD scene with a cube and a sphere:

  ```bash
    python scripts/write_random_scene.py scenes/scene1.usda
  ```

- Inspect the result with USDView:

  ```bash
  usdview scenes/scene1.usda
  ```

### 2. Composing Scenes

Merge `scene_hero.usda` and `scene1.usda` into `merged.usda`:

  ```bash
     python scripts/simple_composer.py scenes/scene_hero.usda scenes/scene1.usda scenes/merged.usda
  ```

- Reads both input USDA files.  
- Copies prim hierarchies, metadata, relationship targets, and variant sets.  
- Writes the combined scene out to `merged.usda`.  

### 3. Validating the Composition

Verify that `merged.usda` exactly reflects all data from the source scenes:

  ```bash
     python scripts/validate_composed.py scenes/scene_hero.usda scenes/scene1.usda scenes/merged.usda
  ```

- Compares the composed USD against the original scenes.
- Checks for missing prims, metadata differences, relationship targets, and variant sets.
- Outputs validation results to the console.
- If the validation passes, it will print "Validation PASSED."
- If there are mismatches, it will list them and exit with a non-zero code.
### Validation Output
- If the validation passes, you will see:  
  ```
  Validation PASSED: composed USD contains all expected data.
  ```
- If there are issues, the script will output details like:
    ```
    Validation FAILED:
    - Missing prims: /World/Cube
    - Metadata differences: /World/Cube:color
    - Relationship issues: /World/Cube has no relationship to /World/Sphere
    - Variant issues: /World/Cube has no variant set
    ```
---

## Example Workflow

```bash
 # 1.Write a random USD scene
$ python scripts/write_random_scene.py scenes/scene1.usda
Writing random USD scene to scenes/scene1.usda
$ usdview scenes/scene1.usda

Review scene1.usda
$ usdview scene1.usda

# 2. Compose
$ python scripts/simple_composer.py scenes/scene_hero.usda scenes/scene1.usda scenes/merged.usda
Composed scene_hero.usda + scene1.usda → merged.usda

# 3. Validate
$ python scripts/validate_composed.py scenes/scene_hero.usda scenes/scene1.usda scenes/merged.usda
Validation PASSED: composed USD contains all expected data.
```

---

## Troubleshooting

- Ensure that the USD Python bindings (`pxr.Usd`, `pxr.Sdf`) are importable.  
- If you hit “module not found” errors, double-check your USD installation and `PYTHONPATH`.  
- Use absolute paths if your input USDA files are not in the current directory.  

---

## Contributing & License

Feel free to open issues or pull requests to improve the composer, add new features (payloads, references, inheritances, etc.), or enhance the demo scripts.  

This project is released under the GNU General Public License. See [LICENSE](LICENSE) for details.