A bot to help with requests to add software installations to the [EESSI software layer](https://github.com/EESSI/software-layer)

GitHub App implemented in ``eessi_bot_software_layer.py``

Script to start app: ``run.sh``

Requires:

* Python 3
* **PyGitHub**: Python library to use GitHub API v3
  * https://github.com/PyGithub/PyGithub
  * API: https://pygithub.readthedocs.io/en/latest/reference.html
* **Waitress**: production-quality pure-Python WSGI server
  * https://docs.pylonsproject.org/projects/waitress/en/stable/
* **PyGHee**: Python library to facilitate creating a GitHub App implemented in Python
  * https://github.com/boegel/PyGHee

```
pip3 install --user -r requirements.txt
```
