import os
import shutil
import sys
import uuid
from dataclasses import dataclass
from decimal import Decimal

from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QColor, QFont, QIcon, QPixmap
from PyQt6.QtWidgets import (
    QApplication, QComboBox, QDateEdit, QDialog, QFileDialog,
    QFormLayout, QGridLayout, QHBoxLayout, QLabel, QLineEdit,
    QMainWindow, QMessageBox, QPushButton, QTableWidget,
    QTableWidgetItem, QTextEdit, QVBoxLayout, QWidget,
)

from db import get_connection

if getattr(sys, 'frozen', False):
    _BUNDLE = sys._MEIPASS
    _DATA   = os.path.dirname(sys.executable)
else:
    _BUNDLE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    _DATA   = _BUNDLE

RESOURCES_DIR = os.path.join(_BUNDLE, "resources")
PHOTOS_DIR    = os.path.join(_DATA,   "resources", "photos")
ICON_ICO      = os.path.join(RESOURCES_DIR, "icon.ico")
ICON_PNG      = os.path.join(RESOURCES_DIR, "icon.png")
PICTURE_PNG   = os.path.join(RESOURCES_DIR, "picture.png")


def _find_photo(file_name: str) -> str:
    p = os.path.join(PHOTOS_DIR, file_name)
    if os.path.exists(p):
        return p
    p2 = os.path.join(_BUNDLE, "resources", "photos", file_name)
    if os.path.exists(p2):
        return p2
    return PICTURE_PNG

COLOR_WHITE         = "#FFFFFF"   # основной фон
COLOR_SECOND        = "#ABCFCE"   # дополнительный фон
COLOR_ACCENT        = "#546F94"   # акцент (целевые действия)
COLOR_DISCOUNT_HIGH = "#23E1EF"   # скидка > 25%
COLOR_ZERO_STOCK    = "#ABCFCE"   # нет на складе — доп. фон
COLOR_TEXT          = "#000000"   # текст везде чёрный
DISCOUNT_THRESHOLD  = 25
FONT_FAMILY         = "Comic Sans MS"

DISCOUNT_RANGES = [
    "Все диапазоны",
    "0–10.99%",
    "11–24.99%",
    "25% и более",
]


def app_font(size: int = 11) -> QFont:
    return QFont(FONT_FAMILY, size)


def set_window_icon(widget) -> None:
    if os.path.exists(ICON_ICO):
        widget.setWindowIcon(QIcon(ICON_ICO))


def global_stylesheet() -> str:
    return f"""
        QWidget, QLabel, QPushButton, QLineEdit, QComboBox, QDateEdit,
        QTextEdit, QSpinBox, QTableWidget, QTableWidgetItem, QDialog,
        QMainWindow {{
            color: {COLOR_TEXT};
            font-family: "{FONT_FAMILY}";
        }}
        QWidget {{
            background-color: {COLOR_WHITE};
        }}
        QLineEdit, QComboBox, QDateEdit, QTextEdit, QSpinBox {{
            background-color: {COLOR_WHITE};
            color: {COLOR_TEXT};
            border: 1px solid {COLOR_ACCENT};
            padding: 4px;
        }}
        QTableWidget {{
            background-color: {COLOR_WHITE};
            color: {COLOR_TEXT};
            gridline-color: {COLOR_ACCENT};
        }}
        QTableWidget::item {{
            color: {COLOR_TEXT};
        }}
        QHeaderView::section {{
            background-color: {COLOR_SECOND};
            color: {COLOR_TEXT};
            border: 1px solid {COLOR_ACCENT};
            padding: 4px;
        }}
    """


def style_accent_button(btn: QPushButton) -> None:
    btn.setStyleSheet(
        f"background-color:{COLOR_ACCENT};color:{COLOR_TEXT};"
        f'font-family:"{FONT_FAMILY}";padding:6px 14px;border:none;'
    )


def style_secondary_button(btn: QPushButton) -> None:
    btn.setStyleSheet(
        f"background-color:{COLOR_SECOND};color:{COLOR_TEXT};"
        f'font-family:"{FONT_FAMILY}";padding:6px 14px;border:none;'
    )


def style_panel(widget: QWidget) -> None:
    widget.setStyleSheet(
        f"background-color:{COLOR_SECOND};color:{COLOR_TEXT};"
        f'font-family:"{FONT_FAMILY}";'
    )


def make_title_label(text: str, size: int = 22) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet(
        f'font-family:"{FONT_FAMILY}";font-size:{size}px;font-weight:bold;'
        f"color:{COLOR_TEXT};"
    )
    return lbl


def logo_pixmap(max_w: int = 160, max_h: int = 90) -> QPixmap | None:
    """Логотип без искажения пропорций и цвета."""
    if not os.path.exists(ICON_PNG):
        return None
    pix = QPixmap(ICON_PNG)
    if pix.isNull():
        return None
    if pix.width() <= max_w and pix.height() <= max_h:
        return pix
    return pix.scaled(
        max_w, max_h,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )


def apply_dialog_chrome(dialog: QDialog, header_text: str) -> QVBoxLayout:
    dialog.setStyleSheet(
        f"QDialog {{ background-color: {COLOR_WHITE}; color: {COLOR_TEXT}; "
        f'font-family: "{FONT_FAMILY}"; }}'
    )
    set_window_icon(dialog)
    root = QVBoxLayout(dialog)
    root.addWidget(make_title_label(header_text))
    return root


@dataclass
class UserInfo:
    user_id: int | None
    full_name: str
    role_name: str


def show_error(parent, text):
    QMessageBox.critical(parent, "Ошибка", text)


def show_warn(parent, text):
    QMessageBox.warning(parent, "Предупреждение", text)


class DataService:
    @staticmethod
    def auth(login: str, password: str):
        conn = get_connection()
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute(
                "SELECT u.user_id, u.full_name, r.role_name "
                "FROM users u JOIN roles r ON r.role_id = u.role_id "
                "WHERE u.login = %s AND u.password_plain = %s",
                (login, password),
            )
            row = cur.fetchone()
            return UserInfo(row["user_id"], row["full_name"], row["role_name"]) if row else None
        finally:
            conn.close()

    @staticmethod
    def get_products():
        conn = get_connection()
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute(
                "SELECT p.product_id, p.article, p.name, c.name AS category_name, "
                "p.description_text, m.name AS manufacturer_name, s.name AS supplier_name, "
                "p.price, p.discount_percent, p.unit_name, p.stock_quantity, p.photo_file "
                "FROM products p "
                "JOIN categories c ON c.category_id = p.category_id "
                "JOIN manufacturers m ON m.manufacturer_id = p.manufacturer_id "
                "JOIN suppliers s ON s.supplier_id = p.supplier_id "
                "ORDER BY p.product_id"
            )
            return cur.fetchall()
        finally:
            conn.close()

    @staticmethod
    def get_categories():
        conn = get_connection()
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT category_id, name FROM categories ORDER BY name")
            return cur.fetchall()
        finally:
            conn.close()

    @staticmethod
    def get_manufacturers():
        conn = get_connection()
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT manufacturer_id, name FROM manufacturers ORDER BY name")
            return cur.fetchall()
        finally:
            conn.close()

    @staticmethod
    def get_suppliers():
        conn = get_connection()
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT supplier_id, name FROM suppliers ORDER BY name")
            return cur.fetchall()
        finally:
            conn.close()

    @staticmethod
    def get_product_by_id(product_id: int):
        conn = get_connection()
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute(
                "SELECT p.product_id, p.article, p.name, p.category_id, p.description_text, "
                "p.manufacturer_id, p.supplier_id, p.price, p.unit_name, "
                "p.stock_quantity, p.discount_percent, p.photo_file "
                "FROM products p WHERE p.product_id = %s",
                (product_id,),
            )
            return cur.fetchone()
        finally:
            conn.close()

    @staticmethod
    def save_product(model: dict):
        conn = get_connection()
        try:
            cur = conn.cursor()
            if model.get("product_id"):
                cur.execute(
                    "UPDATE products SET article=%s, name=%s, category_id=%s, description_text=%s, "
                    "manufacturer_id=%s, supplier_id=%s, price=%s, unit_name=%s, "
                    "stock_quantity=%s, discount_percent=%s, photo_file=%s WHERE product_id=%s",
                    (model["article"], model["name"], model["category_id"], model["description_text"],
                     model["manufacturer_id"], model["supplier_id"], model["price"], model["unit_name"],
                     model["stock_quantity"], model["discount_percent"], model["photo_file"], model["product_id"]),
                )
            else:
                cur.execute(
                    "INSERT INTO products(article,name,category_id,description_text,manufacturer_id,"
                    "supplier_id,price,unit_name,stock_quantity,discount_percent,photo_file) "
                    "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    (model["article"], model["name"], model["category_id"], model["description_text"],
                     model["manufacturer_id"], model["supplier_id"], model["price"], model["unit_name"],
                     model["stock_quantity"], model["discount_percent"], model["photo_file"]),
                )
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def product_exists_in_orders(product_id: int) -> bool:
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM order_items WHERE product_id=%s", (product_id,))
            return cur.fetchone()[0] > 0
        finally:
            conn.close()

    @staticmethod
    def delete_product(product_id: int):
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM products WHERE product_id=%s", (product_id,))
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def get_orders():
        conn = get_connection()
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute(
                "SELECT o.order_id, o.order_number, o.article_text, os.status_name, "
                "pp.address_text, o.order_date, o.delivery_date "
                "FROM orders o "
                "JOIN order_statuses os ON os.status_id = o.status_id "
                "JOIN pickup_points pp ON pp.pickup_point_id = o.pickup_point_id "
                "ORDER BY o.order_number"
            )
            return cur.fetchall()
        finally:
            conn.close()

    @staticmethod
    def get_order_statuses():
        conn = get_connection()
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT status_id, status_name FROM order_statuses ORDER BY status_name")
            return cur.fetchall()
        finally:
            conn.close()

    @staticmethod
    def get_pickup_points():
        conn = get_connection()
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT pickup_point_id, address_text FROM pickup_points ORDER BY pickup_point_id")
            return cur.fetchall()
        finally:
            conn.close()

    @staticmethod
    def get_order_by_id(order_id: int):
        conn = get_connection()
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT * FROM orders WHERE order_id=%s", (order_id,))
            return cur.fetchone()
        finally:
            conn.close()

    @staticmethod
    def get_next_order_number():
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT COALESCE(MAX(order_number), 0) + 1 FROM orders")
            return cur.fetchone()[0]
        finally:
            conn.close()

    @staticmethod
    def get_next_pickup_code():
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT COALESCE(MAX(pickup_code), 900) + 1 FROM orders")
            return cur.fetchone()[0]
        finally:
            conn.close()

    @staticmethod
    def parse_article_pairs(text: str):
        tokens = [x.strip() for x in (text or "").split(",") if x.strip()]
        if len(tokens) < 2 or len(tokens) % 2 != 0:
            raise ValueError("Артикулы задаются парами: артикул, количество.")
        pairs = []
        for i in range(0, len(tokens), 2):
            try:
                qty = int(tokens[i + 1])
            except Exception:
                raise ValueError("Количество должно быть целым числом.")
            if qty <= 0:
                raise ValueError("Количество должно быть больше 0.")
            pairs.append((tokens[i], qty))
        return pairs

    @staticmethod
    def save_order(model: dict):
        conn = get_connection()
        try:
            pairs = DataService.parse_article_pairs(model["article_text"])
            cur = conn.cursor()
            article_ids = {}
            for article, _ in pairs:
                cur.execute("SELECT product_id FROM products WHERE article=%s", (article,))
                row = cur.fetchone()
                if not row:
                    raise ValueError(f"Артикул {article} не найден.")
                article_ids[article] = row[0]

            if model.get("order_id"):
                cur.execute(
                    "UPDATE orders SET article_text=%s, order_date=%s, delivery_date=%s, "
                    "pickup_point_id=%s, status_id=%s WHERE order_id=%s",
                    (model["article_text"], model["order_date"], model["delivery_date"],
                     model["pickup_point_id"], model["status_id"], model["order_id"]),
                )
                order_id = model["order_id"]
                cur.execute("DELETE FROM order_items WHERE order_id=%s", (order_id,))
            else:
                cur.execute(
                    "INSERT INTO orders(order_number,article_text,order_date,delivery_date,"
                    "pickup_point_id,client_user_id,pickup_code,status_id) VALUES(%s,%s,%s,%s,%s,%s,%s,%s)",
                    (model["order_number"], model["article_text"], model["order_date"],
                     model["delivery_date"], model["pickup_point_id"], None,
                     model["pickup_code"], model["status_id"]),
                )
                order_id = cur.lastrowid

            for article, qty in pairs:
                cur.execute(
                    "INSERT INTO order_items(order_id,product_id,quantity) VALUES(%s,%s,%s)",
                    (order_id, article_ids[article], qty),
                )
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def delete_order(order_id: int):
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM orders WHERE order_id=%s", (order_id,))
            conn.commit()
        finally:
            conn.close()


class LoginDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.user_data = None
        self.setWindowTitle("Вход")
        self.setMinimumWidth(430)
        root = apply_dialog_chrome(self, "Вход в систему")
        form = QFormLayout()
        self.login_edit = QLineEdit()
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("Логин:", self.login_edit)
        form.addRow("Пароль:", self.password_edit)
        root.addLayout(form)
        buttons = QHBoxLayout()
        btn_login = QPushButton("Войти")
        btn_guest = QPushButton("Войти как гость")
        style_accent_button(btn_login)
        style_secondary_button(btn_guest)
        btn_login.clicked.connect(self.login_click)
        btn_guest.clicked.connect(self.guest_click)
        buttons.addWidget(btn_login)
        buttons.addWidget(btn_guest)
        root.addLayout(buttons)

    def login_click(self):
        login = self.login_edit.text().strip()
        password = self.password_edit.text().strip()
        if not login or not password:
            show_warn(self, "Введите логин и пароль.")
            return
        try:
            user = DataService.auth(login, password)
        except Exception as ex:
            show_error(self, f"Ошибка подключения к БД:\n{ex}")
            return
        if user is None:
            show_error(self, "Неверный логин или пароль.")
            return
        self.user_data = user
        self.accept()

    def guest_click(self):
        self.user_data = UserInfo(None, "Гость", "Гость")
        self.accept()


class ProductFormDialog(QDialog):
    """В5: поставщик = dropdown, производитель = dropdown (оба из БД)."""
    def __init__(self, product_id=None):
        super().__init__()
        self.product_id = product_id
        self.old_photo_file = ""
        self.selected_photo_path = ""
        self.setWindowTitle("Добавление/редактирование товара")
        self.setMinimumWidth(760)
        root = apply_dialog_chrome(self, "Добавление/редактирование товара")
        grid = QGridLayout()
        root.addLayout(grid)

        row = 0
        self.id_label = QLabel("ID товара:")
        self.id_edit  = QLineEdit()
        self.id_edit.setReadOnly(True)
        grid.addWidget(self.id_label, row, 0)
        grid.addWidget(self.id_edit,  row, 1)
        row += 1

        self.article_edit       = QLineEdit()
        self.name_edit          = QLineEdit()
        self.category_combo     = QComboBox()
        self.description_edit   = QTextEdit()
        self.description_edit.setFixedHeight(90)
        self.manufacturer_combo = QComboBox()   # dropdown
        self.supplier_combo     = QComboBox()   # dropdown
        self.price_edit         = QLineEdit()
        self.unit_edit          = QLineEdit()
        self.stock_edit         = QLineEdit()
        self.discount_edit      = QLineEdit()

        for label, widget in [
            ("Артикул:", self.article_edit),
            ("Наименование товара:", self.name_edit),
            ("Категория товара:", self.category_combo),
            ("Описание товара:", self.description_edit),
            ("Производитель:", self.manufacturer_combo),
            ("Поставщик:", self.supplier_combo),
            ("Цена:", self.price_edit),
            ("Единица измерения:", self.unit_edit),
            ("Количество на складе:", self.stock_edit),
            ("Действующая скидка (%):", self.discount_edit),
        ]:
            grid.addWidget(QLabel(label), row, 0)
            grid.addWidget(widget, row, 1)
            row += 1

        photo_row = QHBoxLayout()
        self.photo_label = QLabel()
        self.photo_label.setFixedSize(300, 200)
        self.photo_label.setStyleSheet("border:1px solid #546F94;")
        self.photo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        btn_photo = QPushButton("Выбрать фото")
        btn_photo.clicked.connect(self.choose_photo)
        photo_row.addWidget(self.photo_label)
        photo_row.addWidget(btn_photo)
        root.addLayout(photo_row)

        buttons = QHBoxLayout()
        btn_save = QPushButton("Сохранить")
        btn_back = QPushButton("Назад")
        style_accent_button(btn_save)
        style_secondary_button(btn_back)
        style_accent_button(btn_photo)
        btn_save.clicked.connect(self.save_click)
        btn_back.clicked.connect(self.reject)
        buttons.addWidget(btn_save)
        buttons.addWidget(btn_back)
        root.addLayout(buttons)

        self.load_lookups()
        if self.product_id:
            self.load_product(self.product_id)
        else:
            self.id_label.hide()
            self.id_edit.hide()
            self.set_preview(PICTURE_PNG)

    def load_lookups(self):
        for x in DataService.get_categories():
            self.category_combo.addItem(x["name"], x["category_id"])
        for x in DataService.get_manufacturers():
            self.manufacturer_combo.addItem(x["name"], x["manufacturer_id"])
        for x in DataService.get_suppliers():
            self.supplier_combo.addItem(x["name"], x["supplier_id"])

    def resolve_photo_path(self, photo_file: str):
        if photo_file:
            return _find_photo(os.path.basename(photo_file.strip()))
        return PICTURE_PNG

    def load_product(self, product_id: int):
        row = DataService.get_product_by_id(product_id)
        if not row:
            show_error(self, "Товар не найден.")
            self.reject()
            return
        self.id_edit.setText(str(row["product_id"]))
        self.article_edit.setText(row["article"] or "")
        self.name_edit.setText(row["name"] or "")
        self.description_edit.setPlainText(row["description_text"] or "")
        self.price_edit.setText(str(row["price"]))
        self.unit_edit.setText(row["unit_name"] or "")
        self.stock_edit.setText(str(row["stock_quantity"]))
        self.discount_edit.setText(str(row["discount_percent"]))
        i = self.category_combo.findData(row["category_id"])
        if i >= 0:
            self.category_combo.setCurrentIndex(i)
        j = self.manufacturer_combo.findData(row["manufacturer_id"])
        if j >= 0:
            self.manufacturer_combo.setCurrentIndex(j)
        k = self.supplier_combo.findData(row["supplier_id"])
        if k >= 0:
            self.supplier_combo.setCurrentIndex(k)
        self.old_photo_file = row["photo_file"] or ""
        self.set_preview(self.resolve_photo_path(self.old_photo_file))

    def set_preview(self, file_path: str):
        pix = QPixmap(file_path)
        if pix.isNull():
            self.photo_label.setText("Нет фото")
            return
        self.photo_label.setPixmap(
            pix.scaled(300, 200, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        )

    def choose_photo(self):
        path, _ = QFileDialog.getOpenFileName(self, "Выберите фото", "", "Images (*.png *.jpg *.jpeg *.bmp)")
        if not path:
            return
        pix = QPixmap(path)
        if pix.isNull():
            show_warn(self, "Не удалось прочитать изображение.")
            return
        if pix.width() > 300 or pix.height() > 200:
            show_warn(self, "Размер фото не должен превышать 300x200 пикселей.")
            return
        self.selected_photo_path = path
        self.set_preview(path)

    def save_click(self):
        article = self.article_edit.text().strip()
        name    = self.name_edit.text().strip()
        unit    = self.unit_edit.text().strip()
        desc    = self.description_edit.toPlainText().strip()
        if not article or not name or not unit:
            show_warn(self, "Заполните: артикул, наименование, единица измерения.")
            return
        try:
            price    = Decimal(self.price_edit.text().strip().replace(",", "."))
            stock    = int(self.stock_edit.text().strip())
            discount = Decimal(self.discount_edit.text().strip().replace(",", "."))
        except Exception:
            show_error(self, "Проверьте формат цены, количества и скидки.")
            return
        if price < 0 or stock < 0 or discount < 0:
            show_error(self, "Цена, количество и скидка не могут быть отрицательными.")
            return

        photo_file = self.old_photo_file
        if self.selected_photo_path:
            os.makedirs(PHOTOS_DIR, exist_ok=True)
            ext = os.path.splitext(self.selected_photo_path)[1].lower() or ".png"
            new_name = f"uploaded_{uuid.uuid4().hex}{ext}"
            shutil.copy2(self.selected_photo_path, os.path.join(PHOTOS_DIR, new_name))
            photo_file = f"resources/photos/{new_name}"
            if self.old_photo_file:
                old_path = os.path.join(PHOTOS_DIR, os.path.basename(self.old_photo_file))
                if os.path.exists(old_path):
                    try:
                        os.remove(old_path)
                    except Exception:
                        pass

        try:
            DataService.save_product({
                "product_id":      self.product_id,
                "article":         article,
                "name":            name,
                "category_id":     self.category_combo.currentData(),
                "description_text": desc or None,
                "manufacturer_id": self.manufacturer_combo.currentData(),
                "supplier_id":     self.supplier_combo.currentData(),
                "price":           price,
                "unit_name":       unit,
                "stock_quantity":  stock,
                "discount_percent": discount,
                "photo_file":      photo_file or None,
            })
        except Exception as ex:
            show_error(self, f"Ошибка сохранения:\n{ex}")
            return
        self.accept()


class OrderFormDialog(QDialog):
    def __init__(self, order_id=None):
        super().__init__()
        self.order_id = order_id
        self.generated_pickup_code = 901
        self.setWindowTitle("Добавление/редактирование заказа")
        self.setMinimumWidth(680)
        root = apply_dialog_chrome(self, "Добавление/редактирование заказа")
        form = QFormLayout()
        root.addLayout(form)

        self.order_number_edit  = QLineEdit()
        self.order_number_edit.setReadOnly(True)
        self.articles_edit      = QLineEdit()
        self.status_combo       = QComboBox()
        self.pickup_combo       = QComboBox()
        self.order_date_edit    = QDateEdit()
        self.order_date_edit.setCalendarPopup(True)
        self.order_date_edit.setDisplayFormat("yyyy-MM-dd")
        self.delivery_date_edit = QDateEdit()
        self.delivery_date_edit.setCalendarPopup(True)
        self.delivery_date_edit.setDisplayFormat("yyyy-MM-dd")

        form.addRow("Номер заказа:", self.order_number_edit)
        form.addRow("Артикул:", self.articles_edit)
        form.addRow("Статус заказа:", self.status_combo)
        form.addRow("Адрес пункта выдачи:", self.pickup_combo)
        form.addRow("Дата заказа:", self.order_date_edit)
        form.addRow("Дата выдачи:", self.delivery_date_edit)

        for x in DataService.get_order_statuses():
            self.status_combo.addItem(x["status_name"], x["status_id"])
        for x in DataService.get_pickup_points():
            self.pickup_combo.addItem(f'{x["pickup_point_id"]}. {x["address_text"]}', x["pickup_point_id"])

        if self.order_id:
            self.load_order(self.order_id)
        else:
            self.order_number_edit.setText(str(DataService.get_next_order_number()))
            self.generated_pickup_code = DataService.get_next_pickup_code()
            today = QDate.currentDate()
            self.order_date_edit.setDate(today)
            self.delivery_date_edit.setDate(today.addDays(1))

        buttons = QHBoxLayout()
        btn_save = QPushButton("Сохранить")
        btn_back = QPushButton("Назад")
        style_accent_button(btn_save)
        style_secondary_button(btn_back)
        btn_save.clicked.connect(self.save_click)
        btn_back.clicked.connect(self.reject)
        buttons.addWidget(btn_save)
        buttons.addWidget(btn_back)
        root.addLayout(buttons)

    def load_order(self, order_id: int):
        row = DataService.get_order_by_id(order_id)
        if not row:
            show_error(self, "Заказ не найден.")
            self.reject()
            return
        self.order_number_edit.setText(str(row["order_number"]))
        self.articles_edit.setText(row["article_text"] or "")
        self.generated_pickup_code = int(row["pickup_code"])
        i = self.status_combo.findData(row["status_id"])
        if i >= 0:
            self.status_combo.setCurrentIndex(i)
        j = self.pickup_combo.findData(row["pickup_point_id"])
        if j >= 0:
            self.pickup_combo.setCurrentIndex(j)
        if row["order_date"]:
            dt = row["order_date"]
            self.order_date_edit.setDate(QDate(dt.year, dt.month, dt.day))
        if row["delivery_date"]:
            dt = row["delivery_date"]
            self.delivery_date_edit.setDate(QDate(dt.year, dt.month, dt.day))

    def save_click(self):
        articles = self.articles_edit.text().strip()
        if not articles:
            show_warn(self, "Поле Артикул обязательно.")
            return
        try:
            DataService.parse_article_pairs(articles)
        except Exception as ex:
            show_error(self, str(ex))
            return
        try:
            DataService.save_order({
                "order_id": self.order_id,
                "order_number": int(self.order_number_edit.text()),
                "article_text": articles,
                "status_id": self.status_combo.currentData(),
                "pickup_point_id": self.pickup_combo.currentData(),
                "order_date": self.order_date_edit.date().toString("yyyy-MM-dd"),
                "delivery_date": self.delivery_date_edit.date().toString("yyyy-MM-dd"),
                "pickup_code": self.generated_pickup_code,
            })
        except Exception as ex:
            show_error(self, f"Ошибка сохранения:\n{ex}")
            return
        self.accept()


class OrdersDialog(QDialog):
    def __init__(self, user_data: UserInfo, parent=None):
        super().__init__(parent)
        self.user_data = user_data
        self.setWindowTitle("Заказы")
        self.resize(1200, 640)
        root = apply_dialog_chrome(self, "Список заказов")
        top = QHBoxLayout()
        top.addStretch()
        self.btn_add    = QPushButton("Добавить заказ")
        self.btn_edit   = QPushButton("Редактировать заказ")
        self.btn_delete = QPushButton("Удалить заказ")
        btn_back        = QPushButton("Назад")
        style_accent_button(self.btn_add)
        style_secondary_button(self.btn_edit)
        style_secondary_button(self.btn_delete)
        style_secondary_button(btn_back)
        self.btn_add.clicked.connect(self.add_order)
        self.btn_edit.clicked.connect(self.edit_order)
        self.btn_delete.clicked.connect(self.delete_order)
        btn_back.clicked.connect(self.close)
        for b in (self.btn_add, self.btn_edit, self.btn_delete, btn_back):
            top.addWidget(b)
        root.addLayout(top)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            ["Номер", "Артикул заказа", "Статус", "Пункт выдачи", "Дата заказа", "Дата выдачи"]
        )
        self.table.doubleClicked.connect(self.double_click_order)
        root.addWidget(self.table)

        is_admin = self.user_data.role_name == "Администратор"
        self.btn_add.setVisible(is_admin)
        self.btn_edit.setVisible(is_admin)
        self.btn_delete.setVisible(is_admin)
        self.load_orders()

    def load_orders(self):
        rows = DataService.get_orders()
        self.table.setRowCount(len(rows))
        for i, x in enumerate(rows):
            self.table.setItem(i, 0, QTableWidgetItem(str(x["order_number"])))
            self.table.setItem(i, 1, QTableWidgetItem(x["article_text"] or ""))
            self.table.setItem(i, 2, QTableWidgetItem(x["status_name"] or ""))
            self.table.setItem(i, 3, QTableWidgetItem(x["address_text"] or ""))
            self.table.setItem(i, 4, QTableWidgetItem(str(x["order_date"] or "")))
            self.table.setItem(i, 5, QTableWidgetItem(str(x["delivery_date"] or "")))
            self.table.item(i, 0).setData(Qt.ItemDataRole.UserRole, x["order_id"])
        self.table.resizeColumnsToContents()

    def current_order_id(self):
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def add_order(self):
        if self.user_data.role_name == "Администратор" and OrderFormDialog(None).exec():
            self.load_orders()

    def edit_order(self):
        if self.user_data.role_name != "Администратор":
            return
        order_id = self.current_order_id()
        if not order_id:
            show_warn(self, "Выберите заказ для редактирования.")
            return
        if OrderFormDialog(order_id).exec():
            self.load_orders()

    def double_click_order(self):
        if self.user_data.role_name == "Администратор":
            self.edit_order()

    def delete_order(self):
        if self.user_data.role_name != "Администратор":
            return
        order_id = self.current_order_id()
        if not order_id:
            show_warn(self, "Выберите заказ для удаления.")
            return
        if QMessageBox.question(self, "Подтверждение", "Удалить выбранный заказ?") != QMessageBox.StandardButton.Yes:
            return
        try:
            DataService.delete_order(order_id)
        except Exception as ex:
            show_error(self, f"Ошибка удаления:\n{ex}")
            return
        self.load_orders()


class ProductsWindow(QMainWindow):
    def __init__(self, user_data: UserInfo):
        super().__init__()
        self.user_data = user_data
        self.products  = []
        self.product_editor_opened = False

        self.setWindowTitle("Список товаров")
        self.resize(1600, 820)
        set_window_icon(self)
        self.setStyleSheet(
            f"QMainWindow {{ background-color: {COLOR_WHITE}; color: {COLOR_TEXT}; "
            f'font-family: "{FONT_FAMILY}"; }}'
        )

        root = QWidget()
        self.setCentralWidget(root)
        main = QVBoxLayout(root)

        header_panel = QWidget()
        style_panel(header_panel)
        header = QGridLayout(header_panel)
        logo = QLabel()
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pix = logo_pixmap()
        if pix is not None:
            logo.setPixmap(pix)
        title = make_title_label("ООО «Обувь» — Список товаров", 26)
        self.role_label = QLabel(f"Роль: {self._role_caption(user_data.role_name)}")
        self.user_label = QLabel(f"Пользователь: {user_data.full_name}")
        self.btn_orders = QPushButton("Заказы")
        style_secondary_button(self.btn_orders)
        self.btn_orders.clicked.connect(self.open_orders)
        btn_logout = QPushButton("Выход")
        style_accent_button(btn_logout)
        btn_logout.clicked.connect(self.logout)

        right = QVBoxLayout()
        right.addWidget(self.role_label, alignment=Qt.AlignmentFlag.AlignRight)
        right.addWidget(self.user_label, alignment=Qt.AlignmentFlag.AlignRight)
        right.addWidget(self.btn_orders, alignment=Qt.AlignmentFlag.AlignRight)
        right.addWidget(btn_logout, alignment=Qt.AlignmentFlag.AlignRight)
        header.addWidget(logo, 0, 0)
        header.addWidget(title, 0, 1)
        header.addLayout(right, 0, 2)
        header.setColumnStretch(1, 1)
        main.addWidget(header_panel)

        self.filter_wrap = QWidget()
        style_panel(self.filter_wrap)
        fl = QHBoxLayout(self.filter_wrap)
        fl.addWidget(QLabel("Поиск:"))
        self.search_edit = QLineEdit()
        fl.addWidget(self.search_edit)
        fl.addWidget(QLabel("Диапазон скидки:"))
        self.discount_range_combo = QComboBox()
        self.discount_range_combo.addItems(DISCOUNT_RANGES)
        fl.addWidget(self.discount_range_combo)
        fl.addWidget(QLabel("Сортировка:"))
        self.sort_combo = QComboBox()
        self.sort_combo.addItems([
            "Без сортировки",
            "Цена (по возрастанию)",    "Цена (по убыванию)",
            "Остаток (по возрастанию)", "Остаток (по убыванию)",
        ])
        fl.addWidget(self.sort_combo)
        main.addWidget(self.filter_wrap)

        self.admin_wrap = QWidget()
        style_panel(self.admin_wrap)
        al = QHBoxLayout(self.admin_wrap)
        self.btn_add    = QPushButton("Добавить товар")
        self.btn_edit   = QPushButton("Редактировать товар")
        self.btn_delete = QPushButton("Удалить товар")
        style_accent_button(self.btn_add)
        style_secondary_button(self.btn_edit)
        style_secondary_button(self.btn_delete)
        for b in (self.btn_add, self.btn_edit, self.btn_delete):
            al.addWidget(b)
        al.addStretch()
        main.addWidget(self.admin_wrap)

        self.table = QTableWidget()
        self.table.setColumnCount(12)
        self.table.setHorizontalHeaderLabels([
            "Фото", "Артикул", "Наименование", "Категория", "Описание",
            "Производитель", "Поставщик", "Цена", "Цена со скидкой",
            "Ед.", "Остаток", "Скидка",
        ])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.doubleClicked.connect(self.row_double_click)
        main.addWidget(self.table)

        self.btn_add.clicked.connect(self.add_product)
        self.btn_edit.clicked.connect(self.edit_product)
        self.btn_delete.clicked.connect(self.delete_product)
        self.search_edit.textChanged.connect(self.apply_filters)
        self.discount_range_combo.currentTextChanged.connect(self.apply_filters)
        self.sort_combo.currentTextChanged.connect(self.apply_filters)

        self.apply_role_rules()
        self.load_products()

    def _role_caption(self, role_name: str):
        return "Клиент" if role_name == "Авторизированный клиент" else role_name

    def is_admin(self):
        return self.user_data.role_name == "Администратор"

    def is_manager_or_admin(self):
        return self.user_data.role_name in ("Менеджер", "Администратор")

    def apply_role_rules(self):
        self.filter_wrap.setVisible(self.is_manager_or_admin())
        self.admin_wrap.setVisible(self.is_admin())
        self.btn_orders.setVisible(self.is_manager_or_admin())

    def load_products(self):
        self.products = DataService.get_products()
        self.apply_filters()

    def photo_pixmap(self, photo_file: str):
        path = _find_photo(os.path.basename(photo_file)) if photo_file else PICTURE_PNG
        pix = QPixmap(path)
        return pix if not pix.isNull() else QPixmap(PICTURE_PNG)

    def apply_filters(self):
        data = list(self.products)
        if self.is_manager_or_admin():
            text          = self.search_edit.text().strip().lower()
            discount_range = self.discount_range_combo.currentText()
            sort_mode     = self.sort_combo.currentText()

            # Фильтр по диапазону скидки
            if discount_range == "0–10.99%":
                data = [x for x in data if Decimal(str(x.get("discount_percent") or 0)) < 11]
            elif discount_range == "11–24.99%":
                data = [
                    x for x in data
                    if 11 <= Decimal(str(x.get("discount_percent") or 0)) < 25
                ]
            elif discount_range == "25% и более":
                data = [x for x in data if Decimal(str(x.get("discount_percent") or 0)) >= 25]

            if text:
                def hit(row):
                    fields = [row.get(k) for k in ("article", "name", "category_name",
                              "description_text", "manufacturer_name", "supplier_name", "unit_name")]
                    return any(text in str(v or "").lower() for v in fields)
                data = [x for x in data if hit(x)]

            key_map = {
                "Цена (по возрастанию)":    (lambda r: float(r.get("price") or 0),        False),
                "Цена (по убыванию)":       (lambda r: float(r.get("price") or 0),        True),
                "Остаток (по возрастанию)": (lambda r: int(r.get("stock_quantity") or 0), False),
                "Остаток (по убыванию)":    (lambda r: int(r.get("stock_quantity") or 0), True),
            }
            if sort_mode in key_map:
                fn, rev = key_map[sort_mode]
                data.sort(key=fn, reverse=rev)

        self.fill_table(data)

    def fill_table(self, rows):
        self.table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            pix = self.photo_pixmap(row.get("photo_file") or "")
            lbl = QLabel()
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setPixmap(pix.scaled(90, 60, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            self.table.setCellWidget(i, 0, lbl)

            price    = Decimal(str(row.get("price") or 0))
            discount = Decimal(str(row.get("discount_percent") or 0))
            final    = (price * (Decimal("100") - discount) / Decimal("100")).quantize(Decimal("0.01"))

            values = [
                row.get("article") or "", row.get("name") or "",
                row.get("category_name") or "", row.get("description_text") or "",
                row.get("manufacturer_name") or "", row.get("supplier_name") or "",
                f"{price:.2f}", f"{final:.2f}",
                row.get("unit_name") or "", str(row.get("stock_quantity") or 0),
                f"{discount:.2f}",
            ]
            for c, v in enumerate(values, start=1):
                self.table.setItem(i, c, QTableWidgetItem(v))

            self.table.item(i, 1).setData(Qt.ItemDataRole.UserRole, row["product_id"])

            price_item = self.table.item(i, 7)
            if discount > 0:
                f = price_item.font()
                f.setStrikeOut(True)
                price_item.setFont(f)
                price_item.setForeground(QColor(COLOR_TEXT))

            if discount > DISCOUNT_THRESHOLD:
                row_color = QColor(COLOR_DISCOUNT_HIGH)
            elif int(row.get("stock_quantity") or 0) == 0:
                row_color = QColor(COLOR_ZERO_STOCK)
            else:
                row_color = QColor(COLOR_WHITE)

            for col in range(1, self.table.columnCount()):
                cell = self.table.item(i, col)
                if cell:
                    cell.setBackground(row_color)
                    cell.setForeground(QColor(COLOR_TEXT))

        self.table.resizeColumnsToContents()
        self.table.setColumnWidth(0, 100)

    def selected_product_id(self):
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 1)
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def add_product(self):
        if not self.is_admin():
            return
        if self.product_editor_opened:
            show_warn(self, "Окно редактирования уже открыто.")
            return
        self.product_editor_opened = True
        ok = ProductFormDialog(None).exec()
        self.product_editor_opened = False
        if ok:
            self.load_products()

    def edit_product(self):
        if not self.is_admin():
            return
        product_id = self.selected_product_id()
        if not product_id:
            show_warn(self, "Выберите товар для редактирования.")
            return
        if self.product_editor_opened:
            show_warn(self, "Окно редактирования уже открыто.")
            return
        self.product_editor_opened = True
        ok = ProductFormDialog(product_id).exec()
        self.product_editor_opened = False
        if ok:
            self.load_products()

    def row_double_click(self):
        if self.is_admin():
            self.edit_product()

    def delete_product(self):
        if not self.is_admin():
            return
        product_id = self.selected_product_id()
        if not product_id:
            show_warn(self, "Выберите товар для удаления.")
            return
        if DataService.product_exists_in_orders(product_id):
            show_warn(self, "Товар присутствует в заказе. Удаление невозможно.")
            return
        if QMessageBox.question(self, "Подтверждение", "Удалить выбранный товар?") != QMessageBox.StandardButton.Yes:
            return
        try:
            DataService.delete_product(product_id)
        except Exception as ex:
            show_error(self, f"Ошибка удаления:\n{ex}")
            return
        self.load_products()

    def open_orders(self):
        if self.is_manager_or_admin():
            OrdersDialog(self.user_data, self).exec()

    def logout(self):
        self.close()
        login = LoginDialog()
        if login.exec():
            self.next_window = ProductsWindow(login.user_data)
            self.next_window.show()


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setFont(app_font(11))
    app.setStyleSheet(global_stylesheet())
    set_window_icon(app)
    login = LoginDialog()
    if not login.exec():
        sys.exit(0)
    window = ProductsWindow(login.user_data)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

# Шаг 11.1. Зафиксируйте локальный git-коммит (модули 2-4)
# Что делаем
# Сделайте локальный коммит после реализации функционала модулей 2–4.
# Команды/код
# cd C:\shoe_store_2026_pu_python
# git init
# git add app
# git commit -m "Реализованы модули 2-4 (Python, Вариант 1 2026)"

# Шаг 12. Подготовьте блок-схему алгоритма по ГОСТ и сохраните PDF
# Что делаем
# Оформите блок-схему алгоритма разработки приложения согласно ГОСТ 19.701-90.
# Команды/код
# 1. Откройте draw.io (diagrams.net).
# 2. Создайте новую схему: File -> New -> Blank Diagram.
# 3. Выставьте формат страницы A4 (Меню Файл -> Параметры страницы).
# 4. Соберите блок-схему по ГОСТ 19.701-90:
# • Блок начала/конца (овал): Начало.
# • Процесс (прямоугольник): Открыть окно входа.
# • Ввод/вывод (параллелограмм): Ввод логина и пароля / выбор "Войти как гость".
# 43
# • Решение (ромб): Гость?.
# • Процесс: Показать список товаров (роль Гость) (ветка Да).
# • Решение: Логин/пароль верны? (ветка Нет -> Сообщение об ошибке -> возврат к вводу).
# • Процесс: Определить роль (клиент/менеджер/администратор) (ветка Да).
# • Процесс: Показать список товаров.
# • Процесс: Поиск/фильтр/сортировка.
# • Решение: Роль позволяет редактирование?.
# • Процесс: CRUD товаров и заказов (для менеджера/администратора).
# • Блок начала/конца (овал): Выход.
# 5. Соедините блоки стрелками по потоку выполнения.
# 6. Сохраните исходник схемы:
# • C:\shoe_store_2026_pu_python\docs\algorithm_gost.drawio
# 7. Экспортируйте в PDF:
# • C:\shoe_store_2026_pu_python\docs\algorithm_gost.pdf

# Команды/код
# Создайте файл:
# • C:\shoe_store_2026_pu_python\docs\report_screenshots.docx
# Добавьте скриншоты:
# • окно входа;
# • вход как гость;
# • вход под менеджером;
# • вход под администратором;
# • поиск/фильтрация/сортировка;
# • добавление/редактирование/удаление товара;
# • окно заказов;
# • добавление/редактирование/удаление заказа.

# Шаг 13. Подготовьте DOCX со скриншотами корректной работы
# Что делаем
# Соберите скриншоты основных сценариев.
# Команды/код
# Создайте файл:
# • C:\shoe_store_2026_pu_python\docs\report_screenshots.docx
# Добавьте скриншоты:
# • окно входа;
# • вход как гость;
# • вход под менеджером;
# • вход под администратором;
# • поиск/фильтрация/сортировка;
# • добавление/редактирование/удаление товара;
# • окно заказов;
# • добавление/редактирование/удаление заказа.

# Шаг 14. Экспортируйте SQL-скрипт БД и ER-диаграмму
# Что делаем
# Сохраните итоговую структуру и данные БД.
# Команды/код
# 1. В phpMyAdmin выберите БД shoe2026_pu.
# 2. Вкладка Экспорт -> формат SQL.
# 3. Сохраните как:
# • C:\shoe_store_2026_pu_python\sql\shoe2026_pu.sql
# 4. Вкладка Ещё -> Дизайнер -> экспорт в PDF.
# 5. Сохраните как:
# • C:\shoe_store_2026_pu_python\sql\shoe2026_pu_er.pdf

# Шаг 15. Соберите .exe через PyInstaller
# Что делаем
# Соберите исполняемый файл приложения.
# Команды/код
# cd C:\shoe_store_2026_pu_python\app
# .\.venv\Scripts\activate
# pyinstaller --noconfirm --windowed --onefile --name ShoeStore2026PUApp --icon "..\resources\icon.ico" --add-data "..\resources;resources" --collect-all PyQt6 --collect-all mysql.connector main.py
# Результат:
# • C:\shoe_store_2026_pu_python\app\dist\ShoeStore2026PUApp.exe

# Шаг 16. Подготовьте финальный набор файлов и git-коммит
# Что делаем
# Проверьте комплект итоговых материалов и зафиксируйте локальный коммит.
# Команды/код
# Проверьте наличие:
# • исходный код приложения (структура папок, не архив);
# • dist\ShoeStore2026PUApp.exe;
# • sql\shoe2026_pu.sql;
# • sql\shoe2026_pu_er.pdf;
# • docs\algorithm_gost.pdf;
# • docs\report_screenshots.docx.
# Зафиксируйте итог в локальном git-репозитории:
# cd C:\shoe_store_2026_pu_python
# git add .
# git status
# git commit -m "Финальная версия проекта (Python, Вариант 1 2026)"