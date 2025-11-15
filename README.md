# amino.dorks.fix

**amino.dorks.fix** — a fixed version of the old [aminofix](https://github.com/Minori101/Amino.fix) library, restored to work properly with the Amino API. It works on **[DorksRestAPI](https://github.com/AminoDorks/DorksRestAPI)**.

📢 Telegram: [@aminodorks](https://t.me/aminodorks)

---

## 📦 Installation

```bash
pip install amino.dorks.fix
```

Or from repository:

```bash
git clone https://github.com/misterio060/amino.dorks.fix
cd amino.dorks.fix
pip install .
```

---

## 🔧 Usage

Example of login and performing a check-in:

```python
import aminodorksfix

client = aminodorksfix.Client('go to @aminodorks_bot to get api key')
client.login(email='<EMAIL>', password='<PASSWORD>')
print('logged in', client.profile.nickname)

sub_client = aminodorksfix.SubClient(comId='comId', profile=client.profile)
sub_client.check_in()
```

---

## 📚 Documentation

Currently, documentation is in progress.
For now, you can use old `aminofix` examples since the API is mostly the same.
