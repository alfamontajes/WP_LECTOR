# (c) 2026 Tu Empresa - WP_LECTOR
# Todos los derechos reservados.
# Automatización de control de acceso y registro de imágenes.

import os
import time
import requests
import pandas as pd
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# --- CONFIGURACIÓN DE LA SOLICITUD ---
# Nota: Si buscas mensajes de hoy, WhatsApp suele poner "HOY" en lugar de la fecha.
FECHA_SOLICITADA = "30/04/2026" 
GRUPO_OBJETIVO = "Hidrosanitario y cubiertas Sprbun"
USUARIO_LINUX = os.getlogin()

# --- RUTAS SEGURAS (Ignoradas por Git) ---
FOLDER_FOTOS = "capturas_obra"
EXCEL_REPORTE = f"reporte_nomina_{FECHA_SOLICITADA.replace('/', '-')}.xlsx"

if not os.path.exists(FOLDER_FOTOS):
    os.makedirs(FOLDER_FOTOS)

def configurar_navegador():
    options = Options()
    # Perfil real de Chrome para evitar pedir QR continuamente
    options.add_argument(f"--user-data-dir=/home/{USUARIO_LINUX}/.config/google-chrome/Default")
    
    # Argumentos para evitar cierres inesperados en Linux
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--remote-debugging-port=9222")
    
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)

def descargar_foto(url, nombre_archivo):
    if url:
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                ruta = os.path.join(FOLDER_FOTOS, nombre_archivo)
                with open(ruta, 'wb') as f:
                    f.write(response.content)
                return ruta
        except Exception as e:
            print(f"Error al descargar imagen: {e}")
    return None

def iniciar_wp_lector():
    driver = configurar_navegador()
    wait = WebDriverWait(driver, 30)
    datos_extraidos = []

    try:
        driver.get("https://web.whatsapp.com")
        print("Esperando a que cargue WhatsApp Web... (Asegúrate de que Chrome esté cerrado antes)")
        
        # 1. Buscar el grupo
        print(f"Buscando el grupo: {GRUPO_OBJETIVO}")
        
        # Selector de búsqueda actualizado
        search_xpath = '//div[@aria-label="Caja de texto de búsqueda" or @contenteditable="true"]'
        search_box = wait.until(EC.element_to_be_clickable((By.XPATH, search_xpath)))
        
        search_box.click()
        search_box.send_keys(GRUPO_OBJETIVO)
        time.sleep(3)

        # 2. Entrar al grupo
        grupo_xpath = f'//span[@title="{GRUPO_OBJETIVO}"]'
        grupo = wait.until(EC.element_to_be_clickable((By.XPATH, grupo_xpath)))
        grupo.click()
        print("Entrando al grupo seleccionado...")
        time.sleep(5)

        # 3. Escaneo de mensajes
        print(f"Escaneando contenido para la fecha: {FECHA_SOLICITADA}")
        
        # Buscamos los contenedores de mensajes
        mensajes = driver.find_elements(By.XPATH, '//div[contains(@class, "message-in") or contains(@class, "message-out")]')

        for i, msg in enumerate(mensajes):
            try:
                # Intentamos encontrar imágenes dentro del mensaje
                imagenes = msg.find_elements(By.TAG_NAME, "img")
                
                for img in imagenes:
                    src = img.get_attribute("src")
                    
                    # WhatsApp usa 'blob:' para imágenes temporales en el chat
                    if src and "blob:" in src:
                        # Extraer la descripción (si existe texto junto a la foto)
                        textos = msg.find_elements(By.XPATH, './/span[contains(@class, "selectable-text")]')
                        descripcion = textos[0].text if textos else "Imagen sin descripción"
                        
                        # Extraer hora (usualmente en un span con clase pequeña)
                        # Nota: El XPath de la hora es muy variable, usamos un selector genérico
                        hora_elem = msg.find_elements(By.XPATH, './/div[contains(@class, "copyable-text")]')
                        hora = datetime.now().strftime("%H-%M-%S") # Por defecto si no se halla
                        
                        if hora_elem:
                            meta = hora_elem[0].get_attribute("data-pre-plain-text")
                            if meta:
                                hora = meta.split(']')[0].replace('[', '').replace(':', '-')

                        nombre_archivo = f"{hora}_{i}_obra.jpg"
                        ruta = descargar_foto(src, nombre_archivo)

                        if ruta:
                            datos_extraidos.append({
                                "Fecha": FECHA_SOLICITADA,
                                "Hora": hora,
                                "Descripción": descripcion,
                                "Archivo": nombre_archivo
                            })
                            print(f"Descargado: {nombre_archivo} -> {descripcion}")

            except Exception as e:
                continue

        # 4. Generar reporte
        if datos_extraidos:
            df = pd.DataFrame(datos_extraidos)
            df.to_excel(EXCEL_REPORTE, index=False)
            print(f"\nÉXITO: Se procesaron {len(datos_extraidos)} imágenes.")
            print(f"Reporte: {EXCEL_REPORTE}")
        else:
            print("\nAVISO: No se detectaron imágenes con los criterios actuales.")

    except Exception as e:
        print(f"Error crítico durante la ejecución: {e}")

    finally:
        print("\nEl proceso ha terminado. Puedes revisar el navegador.")
        # driver.quit() # Mantener abierto para depuración

if __name__ == "__main__":
    iniciar_wp_lector()