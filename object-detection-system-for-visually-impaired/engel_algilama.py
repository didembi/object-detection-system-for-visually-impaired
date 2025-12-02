import cv2 #Görüntü işleme
import time
import pyttsx3 #sesli mesaj
import serial #arduino bağlantısı
import queue 
import threading #Multihreading
from ultralytics import YOLO #Nesne algılama
import tkinter as tk #arayüz
from PIL import Image, ImageTk #görüntü yerleştirme

# Arduino bağlantıı
arduino = serial.Serial('COM8', 9600, timeout=0.1)
time.sleep(0.1) # Arduino bağlantısının hazır olması için kısa bekleme

# Konuşma motoru
engine = pyttsx3.init()
engine.setProperty('rate', 150)  # Sesli konuşma hızını ayarla (150 kelime/dk)

# Sesli mesajların sırayla alınması
speech_queue = queue.Queue()

def speak_worker(): #Sesli mesajlar sırayla seslendirir
    while True:
        text = speech_queue.get()
        engine.say(text)
        engine.runAndWait()
        speech_queue.task_done()

# Arka planda sürekli çalışır
threading.Thread(target=speak_worker, daemon=True).start()

# Arduinodan gelen mesafe verisi okuma
def get_distance():
    try:
        line = arduino.readline().decode('utf-8').strip()
        if line.startswith("Ölçülen Mesafe ="):
            return float(line.split('=')[1].strip())
    except Exception:
        return None
    return None

# YOLOv8 model yükle
model = YOLO("yolov8n.pt")

# Kamera
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("Kamera açılamadı")
    exit()

#Açılış arayüzü olusturma Tkinter
class SplashScreen(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Hoş Geldiniz")
        self.geometry("400x300")
        self.configure(bg="white")

        label = tk.Label(self, text="Görme Engelliler İçin Yardımcı Sistem", font=("Arial", 14), bg="white")
        label.pack(expand=True)

        self.after(3000, self.show_main_window)

    def show_main_window(self):
        self.destroy()                # Splash ekranı kapat
        app = BaslatEkrani()          # Başlat ekranını oluştur
        app.mainloop()                # Başlat ekranını göster

class BaslatEkrani(tk.Tk): #Başlat butonu olan arayüz
    def __init__(self):
        super().__init__()
        self.title("Başlat")
        self.geometry("400x300")
        self.configure(bg="#F0F0F0")

        label = tk.Label(self, text="Akıllı Şapka Uygulamasına Hoş Geldiniz", font=("Arial", 14), bg="#F0F0F0")
        label.pack(pady=40)

        start_button = tk.Button(self, text="Başlat", font=("Arial", 12), command=self.start_app, bg="#4CAF50", fg="white", width=15)
        start_button.pack(pady=20) #üstten ve alttan boşluk bırak

    def start_app(self):
        self.destroy()                # Başlat ekranını kapat
        app = Arayuz()                # Ana uygulama arayüzünü başlat
        app.mainloop()

#Ana uygulama arayüzü
class Arayuz(tk.Tk): 
    def __init__(self):
        super().__init__()
        self.title("Görme Engelli Yardımcı")
        self.geometry("720x580")

        self.label = tk.Label(self) #Kameradan algılanan görüntüyü göster
        self.label.pack()

        self.info_label = tk.Label(self, text="Hazır...", font=("Arial", 14))
        self.info_label.pack(pady=10)

        self.detected_objects = set()  # Algılanan nesneleri tekrar etmemek için set
        self.last_reset_time = time.time()
        self.last_msg_time = 0

        self.frame_with_boxes = None
        self.last_box_time = 0  # kutunun gösterilmeye başlandığı zaman

        self.after(10, self.update_frame)

    def update_frame(self):
        ret, frame = cap.read()  # Kameradan bir kare oku
        if ret:
            # Eğer kutulu görüntü varsa ve 3 saniyeden fazla olmamışsa onu göster
            if self.frame_with_boxes is not None and (time.time() - self.last_box_time) < 3:
                display_frame = self.frame_with_boxes.copy()
            else:
                display_frame = frame.copy()
                self.frame_with_boxes = None  # 3 saniyeyi geçtiyse kutu silinir

            img = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)  # BGR’den RGB’ye çevir (Tkinter için)
            img = Image.fromarray(img)                             # Numpy array’i PIL Image’a dönüştür
            imgtk = ImageTk.PhotoImage(image=img)                 # Tkinter uyumlu görsel oluştur
            self.label.imgtk = imgtk
            self.label.config(image=imgtk)                        # Görseli Label’a yerleştir

            distance = get_distance()         # Arduino’dan mesafe al
            
             # Her 15 saniyede bir algılanan nesneler setini temizle
            if time.time() - self.last_reset_time > 15:
                self.detected_objects.clear()
                self.last_reset_time = time.time()

            # Mesafe 50 cm’den azsa nesne algıla
            if distance is not None and distance < 50:
                results = model(frame, verbose=False)[0]
                for box in results.boxes:
                    conf = float(box.conf[0]) #güven skoru
                    if conf < 0.4:
                        continue
                       
                    #Etiket ve konum bilgileri alınır
                    label = model.names[int(box.cls[0])]
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    w = frame.shape[1]
                    center_x = (x1 + x2) // 2

                    # Nesnenin kameradaki konumu (sol, orta, sağ)
                    if center_x < w / 3:
                        pos = "sol"
                    elif center_x > 2 * w / 3:
                        pos = "sag"
                    else:
                        pos = "orta"

                    #Farklı nesne algılandığında işlem yapılır
                    key = f"{label}_{pos}"
                    if key not in self.detected_objects:
                        position_map = {"sol": "left", "orta": "center", "sag": "right"}
                        msg = f"{label} is on the {position_map[pos]} side, {int(distance)} centimeters away."
                        self.detected_objects.add(key)


                        if speech_queue.empty():
                            speech_queue.put(msg)

                        self.info_label.config(text=msg)          # Arayüzde mesajı göster
                        self.last_msg_time = time.time()          # Son mesaj zamanını güncelle

                    # Çerçeveyi çiz ve frame_with_boxes değişkenine kaydet
                    frame_copy = frame.copy()
                    cv2.rectangle(frame_copy, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    cv2.putText(frame_copy, label, (x1, y1 - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                    self.frame_with_boxes = frame_copy
                    self.last_box_time = time.time()
                    break
            else:
                 # 3 saniyeden uzun süre nesne yoksa arayüzde mesajı güncelle
                if time.time() - self.last_msg_time > 3:
                    self.info_label.config(text="No object nearby")

        self.after(100, self.update_frame)


# Programı başlat
if __name__ == "__main__":
    splash = SplashScreen()  # Açılış ekranını oluştur
    splash.mainloop()        # Açılış ekranı kapanana kadar bekle

    # Program bittiğinde kamerayı ve Arduino bağlantısını kapat
    cap.release()
    arduino.close()
