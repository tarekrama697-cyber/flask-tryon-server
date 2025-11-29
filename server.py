import requests
import flet as ft
import os
import logging
from custom_snack_bar import ThemedSnackBar
from utils.helpers import get_base64_data

API_SERVER_URL = os.environ.get(
    "TRYON_API_URL", "http://127.0.0.1:5001/try-on")

# متغيرات عامة
person_file_path = None
clothe_file_path = None
current_pick_type = 0  # 1: شخص, 2: ملابس
image_file_picker = None

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)


def try_on_process(e, page, loader_overlay, loader_ring,
                   person_file_path, clothe_file_path,
                   result_img_display, result_card,
                   result_container, reset_button,
                   download_button, action_row, input_controls):
    if not person_file_path or not clothe_file_path:
        page.open(ThemedSnackBar(
            display_text="الرجاء اختيار صورة الشخص والملابس أولاً.",
            message_type=ThemedSnackBar.TYPE_ERROR,
            duration_seconds=3))
        return

    def show_loader():
        loader_overlay.visible = True
        loader_ring.visible = True
        page.update()

    def hide_loader():
        loader_overlay.visible = False
        loader_ring.visible = False
        page.update()

    page.run_thread(show_loader)

    try:
        person_data = get_base64_data(person_file_path)
        clothe_data = get_base64_data(clothe_file_path)

        if not person_data or not clothe_data:
            raise Exception("فشل في ترميز الصور إلى Base64.")

        response = requests.post(
            API_SERVER_URL,
            json={
                "person_image": person_data["base64"],
                "person_mime_type": person_data["mime_type"],
                "clothe_image": clothe_data["base64"],
                "clothe_mime_type": clothe_data["mime_type"],
            },
            timeout=30
        )

        response.raise_for_status()
        result_data = response.json()

        if result_data.get("status") == "success":
            result_base64 = result_data.get("result_image_base64")

            if result_base64:
                def show_result():
                    result_img_display.src_base64 = result_base64
                    result_img_display.visible = True
                    result_card.visible = True
                    result_container.visible = True
                    reset_button.visible = True
                    download_button.visible = True
                    action_row.visible = True
                    input_controls.visible = False
                    page.open(ThemedSnackBar(
                        display_text="تمت التجربة بنجاح وعرض النتيجة!",
                        message_type=ThemedSnackBar.TYPE_SUCCESS,
                        duration_seconds=3))
                    page.update()

                page.run_thread(show_result)
            else:
                raise Exception("الخادم لم يرجع صورة نتيجة صحيحة.")
        else:
            error_msg = result_data.get("error", "خطأ غير معروف من الخادم.")
            page.run_thread(lambda: page.open(ThemedSnackBar(
                display_text=f"فشل التجربة: {error_msg}",
                message_type=ThemedSnackBar.TYPE_ERROR,
                duration_seconds=5)))

    except requests.exceptions.RequestException as req_ex:
        error_msg = f"خطأ في الاتصال: تأكد من تشغيل الخادم على {API_SERVER_URL}. ({req_ex})"
        logging.error(error_msg)
        page.run_thread(lambda: page.open(ThemedSnackBar(
            display_text=error_msg,
            message_type=ThemedSnackBar.TYPE_ERROR,
            duration_seconds=7)))

    except Exception as ex:
        logging.exception("Unexpected error")
        error_msg = f"حدث خطأ غير متوقع: {ex}"
        page.run_thread(lambda: page.open(ThemedSnackBar(
            display_text=error_msg,
            message_type=ThemedSnackBar.TYPE_ERROR,
            duration_seconds=5)))

    finally:
        page.run_thread(hide_loader)


def pick_result(e: ft.FilePickerResultEvent, page,
                person_img_preview, clothe_img_preview,
                person_card, clothe_card, try_on_button):
    global current_pick_type, person_file_path, clothe_file_path
    if e.files and e.files[0]:
        file_path = e.files[0].path
        if current_pick_type == 1:
            person_file_path = file_path
            person_img_preview.src = file_path
            person_card.visible = True
            person_img_preview.visible = True
        elif current_pick_type == 2:
            clothe_file_path = file_path
            clothe_img_preview.src = file_path
            clothe_card.visible = True
            clothe_img_preview.visible = True
        page.update()
        if person_file_path and clothe_file_path:
            try_on_button.visible = True
            page.update()
    current_pick_type = 0


def pick_person_click(e):
    global current_pick_type, image_file_picker
    current_pick_type = 1
    image_file_picker.pick_files(
        allow_multiple=False, file_type=ft.FilePickerFileType.IMAGE
    )


def pick_clothe_click(e):
    global current_pick_type, image_file_picker
    current_pick_type = 2
    image_file_picker.pick_files(
        allow_multiple=False, file_type=ft.FilePickerFileType.IMAGE
    )
