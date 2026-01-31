```ps1
pipenv run python python/hopilot/hopilot.py --window-title "GGPoker"
.
pipenv run python python/hopilot/hopilot.py --replay-video recordings\1.avi
.
pipenv run python python/hopilot/sort_images.py
.
python rename_copy_files.py dataset
.
pipenv run python find_similar_images.py dataset/train full_image_similarity_report.md
```