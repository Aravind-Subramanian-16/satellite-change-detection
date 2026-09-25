import json

cells = []

def add_markdown(text):
    cells.append({
        "cell_type": "markdown",
        "metadata": {},
        "source": [line + "\n" for line in text.split("\n")]
    })

def add_code(text):
    cells.append({
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [line + "\n" for line in text.split("\n")]
    })

add_markdown("## 1. Setup Environment\nMount Google Drive to access `dataset.zip` and `best_model.pt`.")
add_code("""from google.colab import drive
drive.mount('/content/drive')""")

add_markdown("## 2. Copy and Unzip Dataset\nAssuming `dataset.zip` and `best_model.pt` are in the root of your Google Drive. Adjust the path if they are in a folder (e.g., `/content/drive/MyDrive/satellite_project/`).")
add_code("""!cp "/content/drive/MyDrive/dataset.zip" /content/
!cp "/content/drive/MyDrive/best_model.pt" /content/
!unzip -q /content/dataset.zip -d /content/""")

add_markdown("## 3. Define the Model (MobileNetV2 3D CDNet)")
with open("model.py", "r") as f:
    model_code = f.read()
add_code(model_code)

add_markdown("## 4. Run the Degradation Experiment")
with open("evaluate_degradation.py", "r") as f:
    eval_code = f.read()

# Replace local imports of 'model' so it uses the cell above
eval_code_clean = eval_code.replace("from model import MobileNetV2_3D_CDNet\n", "")
add_code(eval_code_clean)

notebook = {
    "cells": cells,
    "metadata": {
        "colab": {
            "name": "degradation_colab.ipynb",
            "provenance": []
        },
        "kernelspec": {
            "display_name": "Python 3",
            "name": "python3"
        },
        "language_info": {
            "name": "python"
        }
    },
    "nbformat": 4,
    "nbformat_minor": 0
}

with open("degradation_colab.ipynb", "w") as f:
    json.dump(notebook, f, indent=2)
print("Generated degradation_colab.ipynb")
