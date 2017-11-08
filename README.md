### Wifi Manager

A script to change local wifi password

### Installation

```
pip install -r requirements.txt
```

### How to use

- Fill in environments variable in `.env` file
- Create a `.password` file with the current wifi password
- Execute the command:
```
python main.py [--password <your_wifi_password>] [--password-file <path/to/password_file>]
```

