import time
import subprocess
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# --- Configuration ---
# The starting page where the appointment link is located.
# San Francisco Consulate Website
CONSULATE_URL = "https://www.exteriores.gob.es/Consulados/sanfrancisco/es/Comunicacion/Noticias/Paginas/Articulos/Ley-de-la-memoria-democr%C3%A1tica.aspx"
# London Consulate Website
# CONSULATE_URL = "https://www.exteriores.gob.es/Consulados/londres/es/ServiciosConsulares/Paginas/CitaNacionalidadLMD.aspx"
# The exact text of the link we need to click.
LINK_TEXT = "ELEGIR FECHA Y HORA"
# The text that appears on the appointment page when no slots are available.
NO_APPOINTMENTS_MESSAGE = "No hay horas disponibles. Inténtelo de nuevo dentro de unos días."
# The topic for ntfy.sh notifications
NTFY_TOPIC = "cita-alerts-f8x2y9"

def send_notification(title, message):
    """Sends a push notification using ntfy.sh."""
    try:
        subprocess.run([
            'curl',
            '-H', f'Title: {title}',
            '-d', message,
            f'ntfy.sh/{NTFY_TOPIC}'
        ], check=True)
        print("Notification sent successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Failed to send notification: {e}")
    except FileNotFoundError:
        print("'curl' command not found. Please install curl to send notifications.")

def setup_driver():
    """Sets up the Selenium WebDriver for Chrome."""
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    service = ChromeService(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    return driver

def check_for_appointments():
    """
    Main function to navigate to the consulate website and check for appointments.
    """
    print(f"--- Starting San Francisco Check ---")
    driver = setup_driver()
    try:
        # 1. Go to the main consulate page
        print(f"Navigating to: {CONSULATE_URL}")
        driver.get(CONSULATE_URL)
        wait = WebDriverWait(driver, 20)

        # 2. Handle the cookie consent banner
        print("Looking for cookie banner...")
        wait.until(EC.element_to_be_clickable((By.XPATH, "//input[@value='Aceptar']"))).click()
        print("Cookie banner found and clicked.")
        time.sleep(1)
        
        # 3. Find and click the main appointment link
        print(f"Looking for link with text: '{LINK_TEXT}'")
        wait.until(EC.presence_of_element_located((By.PARTIAL_LINK_TEXT, LINK_TEXT))).click()
        print("Link found and clicked.")

        # 4. Handle the welcome alert
        print("Waiting for the 'Welcome / Bienvenido' alert...")
        wait.until(EC.alert_is_present())
        alert = driver.switch_to.alert
        print(f"Alert found with text: '{alert.text}'. Accepting it.")
        alert.accept()
        
        # 5. Handle the CAPTCHA page
        print("Looking for the CAPTCHA page and clicking Continue...")
        wait.until(EC.element_to_be_clickable((By.ID, "idCaptchaButton"))).click()
        print("CAPTCHA page handled.")

        # 6. Check for immediate "No Appointments" message
        try:
            print("Checking for immediate 'No Appointments' message...")
            short_wait = WebDriverWait(driver, 5)
            short_wait.until(EC.presence_of_element_located((By.XPATH, f"//*[contains(text(), '{NO_APPOINTMENTS_MESSAGE}')]")))
            print("STATUS: No appointments available.")
            return # Exit gracefully, no notification needed
        except TimeoutException:
            print("Immediate 'No Appointments' message not found. Proceeding...")

        # 7. Handle the Intermediate "Importante" Dialog
        print("Looking for the 'Importante' dialog and clicking ACEPTAR...")
        wait.until(EC.element_to_be_clickable((By.ID, "bktContinue"))).click()
        print("'Importante' dialog accepted.")

        # 8. Click the Service Link
        print("Looking for the service link...")
        wait.until(EC.element_to_be_clickable((By.PARTIAL_LINK_TEXT, "PRESENTACIÓN DE DOCUMENTACIÓN"))).click()
        print("Service link clicked.")

        # 9. Check for available dates on the calendar
        print("\n>>> Checking for available dates on the calendar...")
        available_dates = wait.until(
            EC.presence_of_all_elements_located((By.XPATH, "//td[@title='DISPONIBLE']/a"))
        )

        if available_dates:
            date_texts = [date_element.get_attribute('textContent') for date_element in available_dates]
            print("\n" + "="*50)
            print(">>> SUCCESS! Appointments are available on the following dates:")
            print(", ".join(date_texts))
            print("="*50 + "\n")
            title = "Cita Consular Disponible! (SF)"
            message = f"Hay citas disponibles en San Francisco en las siguientes fechas: {', '.join(date_texts)}"
            send_notification(title, message)
        else:
            print("\n>>> STATUS: No dates marked as 'DISPONIBLE' were found on the calendar.")
            send_notification("Citas SF: Calendario Vacío", "No se encontraron fechas disponibles en el calendario.")
        
        print("--- Check completed successfully! ---")

    except TimeoutException as e:
        # This will catch a timeout from any of the steps above
        print(f"A step timed out. The website may be down or have changed. Error: {e}")
        send_notification("Error en Bot (SF)", "El script falló por un timeout. Revisa los logs de la Action.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        send_notification("Error en Bot (SF)", f"Error inesperado: {e}")
    finally:
        print("--- Closing browser. ---")
        driver.quit()


if __name__ == "__main__":
    check_for_appointments()
