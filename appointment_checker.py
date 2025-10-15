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
NO_APPOINTMENTS_MESSAGE = "No hay horas disponibles para el servicio seleccionado"
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
    # Run in headless mode (no browser window opens)
    options.add_argument("--headless=new")
    options.add_argument("--window-size=1920,1080")
        # The following options are often needed for running headless Chrome on Linux systems.
    options.add_argument("--no-sandbox") # Bypass OS security model, REQUIRED for Linux
    options.add_argument("--disable-dev-shm-usage") # Overcome limited resource problems
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    
    # Automatically download and manage the correct driver for Chrome
    service = ChromeService(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    return driver

def check_for_appointments():
    """
    Main function to navigate to the consulate website and check for appointments.
    It will retry the entire flow up to 10 times if it fails at any step.
    """
    for i in range(10):
        print(f"--- Starting attempt {i+1}/10 ---")
        driver = setup_driver()
        try:
            # 1. Go to the main consulate page
            print(f"Navigating to: {CONSULATE_URL}")
            driver.get(CONSULATE_URL)
            wait = WebDriverWait(driver, 20)

            # 2. Handle the cookie consent banner
            print("Looking for cookie banner...")
            cookie_accept_button = wait.until(
                EC.element_to_be_clickable((By.XPATH, "//input[@value='Aceptar']"))
            )
            print("Cookie banner found. Clicking 'Aceptar' via JavaScript...")
            driver.execute_script("arguments[0].click();", cookie_accept_button)
            time.sleep(1)
            
            # 3. Find and click the main appointment link
            print(f"Looking for link with text: '{LINK_TEXT}'")
            appointment_link = wait.until(
                EC.presence_of_element_located((By.PARTIAL_LINK_TEXT, LINK_TEXT))
            )
            print("Link found! Clicking to open the appointment page...")
                        driver.execute_script("arguments[0].click();", appointment_link)
            
                        # 5. Handle the welcome alert
                        print("Waiting for the 'Welcome / Bienvenido' alert...")
                        wait.until(EC.alert_is_present())
                        alert = driver.switch_to.alert
                        print(f"Alert found with text: '{alert.text}'. Accepting it.")
                        alert.accept()
            
                        # SF site loads in the same window, so we wait for the iframe to appear.
                        print("Waiting for iframe to load...")
                        wait.until(EC.frame_to_be_available_and_switch_to_it((By.XPATH, "//iframe[contains(@src, 'citaconsular.es')]")))
                        print("Switched to iframe.")
            
            # 6. Handle the CAPTCHA page
            print("Looking for the CAPTCHA page and clicking Continue...")
            captcha_button = wait.until(
                EC.element_to_be_clickable((By.ID, "idCaptchaButton"))
            )
            captcha_button.click()
            print("CAPTCHA page handled.")

            # 7. Handle the Intermediate "Importante" Dialog
            print("Looking for the 'Importante' dialog and clicking ACEPTAR...")
            accept_button = wait.until(
                EC.element_to_be_clickable((By.ID, "bktContinue"))
            )
            accept_button.click()
            print("'Importante' dialog accepted.")

            # 8. Click the Service Link
            print("Looking for the service link...")
            service_link = wait.until(
                EC.element_to_be_clickable((By.PARTIAL_LINK_TEXT, "PRESENTACIÓN DE DOCUMENTACIÓN"))
            )
            service_link.click()
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
                # Send notification
                title = "Cita Consular Disponible! (SF)"
                message = f"Hay citas disponibles en San Francisco en las siguientes fechas: {', '.join(date_texts)}"
                send_notification(title, message)
            else:
                print("\n>>> STATUS: No dates marked as 'DISPONIBLE' were found on the calendar.")
            
            # If we've gotten this far, the check was successful.
            print("--- Check completed successfully! ---")
            return

        except TimeoutException:
            print(f"Attempt {i+1} timed out. Retrying...")
        except Exception as e:
            print(f"Attempt {i+1} failed with an unexpected error: {e}. Retrying...")
        finally:
            print("--- Cleaning up attempt. ---")
            driver.quit()

    print("--- Failed to complete the check after 10 attempts. ---")
    # Send a notification that the script failed
    send_notification("Error en el Bot de Citas (SF)", "El script no pudo completarse después de 10 intentos.")


if __name__ == "__main__":
    check_for_appointments()