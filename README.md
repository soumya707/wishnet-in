# Wish Net Pvt. Ltd. website

This repository contains the code and resources for the website.

## Repository organization

```
.
+-- config.py
+-- README.md
+-- run.py
+-- tox.ini
+-- instance
|   +-- config.py (contains instance specific config)
+-- website
|   +-- __init__.py
|   +-- forms.py (contains class definitions for forms)
|   +-- models.py (contains class definitions used in db)
|   +-- views.py (conatins routes)
|   +-- helpers.py (contains class definitions for MQ Sure API)
|   +-- static
|   |   +-- css
|   |   |   +-- style.css (custom CSS)
|   |   +-- img
|   |   |   +-- (contains images)
|   |   +-- js
|   +-- templates
|   |   +-- (contains HTML templates)
|   |   +-- admin
|   |   |   +-- (templates used for admin)
|   |   +-- security
|   |   |   +-- (templates used for security)
|   +-- security
|   |   +-- __init__.py
|   |   +-- models.py (contains models for Flask-Security)
```
