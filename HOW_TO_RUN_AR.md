# طريقة تشغيل Task 1 على Windows باستخدام Git Bash

## 1) افتح Docker Desktop

افتح برنامج **Docker Desktop** وانتظر حتى يكتمل تشغيله.

بعد ذلك افتح **Git Bash** وانتقل إلى مجلد المشروع:

```bash
cd ~/Desktop/task_one/Brazilian-E-Commerce-Public-Dataset-by-Olist
```

## 2) جهّز ملفات البيانات

فك ضغط بيانات Olist، ثم انسخ ملفات CSV التسعة إلى المجلد:

```text
data/raw
```

تأكد من وجود الملفات:

```bash
ls ./data/raw
```

يجب أن تظهر ملفات البيانات التسعة، ومنها:

```text
olist_customers_dataset.csv
olist_orders_dataset.csv
olist_order_items_dataset.csv
product_category_name_translation.csv
```

## 3) شغّل PostgreSQL

داخل مجلد المشروع نفّذ:

```bash
docker compose up -d
docker compose ps
```

انتظر حتى تظهر حالة PostgreSQL بالشكل التالي:

```text
olist_postgres   Up ... (healthy)
```

تحقق من الاتصال بقاعدة البيانات:

```bash
docker compose exec postgres psql \
  -U olist_user \
  -d olist_db \
  -c "SELECT current_user, current_database();"
```

بيانات قاعدة البيانات:

- اسم قاعدة البيانات: `olist_db`
- المستخدم: `olist_user`
- كلمة المرور: `olist_pass`
- المنفذ: `localhost:5432`

يمكن فتح pgAdmin اختياريًا من:

```text
http://localhost:5050
```

بيانات تسجيل الدخول إلى pgAdmin:

- البريد الإلكتروني: `admin@olist.local`
- كلمة المرور: `admin`

> pgAdmin اختياري، ولا تؤثر مشكلة تشغيله في تحميل البيانات طالما أن `olist_postgres` حالته `healthy`.

## 4) فعّل بيئة Python وثبّت المكتبات

إذا كانت علامة `(.venv)` ظاهرة في بداية سطر Git Bash، فالبيئة مفعّلة بالفعل ويمكنك تجاوز أمر التفعيل.

إذا لم تكن ظاهرة، نفّذ:

```bash
source .venv/Scripts/activate
```

ثم ثبّت المكتبات:

```bash
python -m pip install -r requirements.txt
```

ظهور رسالة `Requirement already satisfied` يعني أن المكتبات مثبتة بنجاح.

## 5) حمّل البيانات إلى PostgreSQL

نفّذ:

```bash
python scripts/load_data.py --data-dir ./data/raw
```

يجب أن تظهر نتائج تحميل الجداول التسعة، وفي النهاية:

```text
All tables loaded successfully.
```

## 6) شغّل استعلامات الاختبار والـ joins

نفّذ:

```bash
cat scripts/test_queries.sql |
  docker compose exec -T postgres psql -U olist_user -d olist_db
```

قارن النتائج مع ملف:

```text
query_output.txt
```

يجب أن تظهر جميع الجداول التسعة، ومنها:

```text
product_category_translation | 71
```

كما يجب أن تعمل استعلامات القراءة والـ joins والـ aggregation وحساب `is_late` دون أخطاء.

## 7) أوقف المشروع

لإيقاف الحاويات مع الاحتفاظ بالبيانات:

```bash
docker compose down
```

لا تستخدم الأمر التالي إلا إذا أردت حذف قاعدة البيانات بالكامل وإعادة تحميلها من البداية:

```bash
docker compose down -v
```

## ملف التسليم

التقرير الجاهز للرفع إلى Classroom هو:

