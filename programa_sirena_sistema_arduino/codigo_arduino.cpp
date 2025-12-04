// Pines
const int buzzerPin       = 8;
const int ledVerdePin     = 9;
const int ledRojoPin      = 10;
const int ledAmarilloPin  = 11;

String comando = "";

// Estado de la sirena
bool sirenaActiva = false;

// Parámetros de la sirena (barrido de frecuencia)
const int freqMin = 800;    // Hz
const int freqMax = 1800;   // Hz
int freqActual = freqMin;   // Frecuencia actual
int deltaFreq = 40;         // Paso de frecuencia
unsigned long ultimoPasoSirena = 0;
const unsigned long intervaloSirena = 20;  // ms entre cambios (más chico = más rápido el barrido)

// Parpadeo del LED amarillo (1 segundo en total)
void parpadeoAmarillo() {
  digitalWrite(ledAmarilloPin, HIGH);
  delay(500);               // 0,5 s encendido
  digitalWrite(ledAmarilloPin, LOW);
  delay(500);               // 0,5 s apagado
}

// Actualiza el sonido de la sirena (sube y baja frecuencia)
void actualizarSirena() {
  if (!sirenaActiva) {
    // Si la sirena no está activa, aseguramos que el buzzer esté apagado
    noTone(buzzerPin);
    return;
  }

  unsigned long ahora = millis();
  if (ahora - ultimoPasoSirena >= intervaloSirena) {
    ultimoPasoSirena = ahora;

    // Reproducir el tono actual
    tone(buzzerPin, freqActual);

    // Actualizar frecuencia para el siguiente paso
    freqActual += deltaFreq;

    // Invertir el sentido del barrido cuando llegamos a los límites
    if (freqActual >= freqMax || freqActual <= freqMin) {
      deltaFreq = -deltaFreq;
    }
  }
}

void setup() {
  Serial.begin(9600);

  pinMode(buzzerPin, OUTPUT);
  pinMode(ledVerdePin, OUTPUT);
  pinMode(ledRojoPin, OUTPUT);
  pinMode(ledAmarilloPin, OUTPUT);

  // Estado inicial: sirena OFF → verde encendido, rojo apagado
  noTone(buzzerPin);
  digitalWrite(ledVerdePin, HIGH);
  digitalWrite(ledRojoPin, LOW);
  digitalWrite(ledAmarilloPin, LOW);
}

void loop() {
  // Leer comandos del puerto serie
  if (Serial.available()) {
    comando = Serial.readStringUntil('\n');
    comando.trim();   // Quita espacios / saltos de línea

    if (comando == "ON") {
      // Activar sirena
      sirenaActiva = true;
      digitalWrite(ledRojoPin, HIGH);
      digitalWrite(ledVerdePin, LOW);

      // Indicar transmisión
      parpadeoAmarillo();
    }
    else if (comando == "OFF") {
      // Desactivar sirena
      sirenaActiva = false;
      noTone(buzzerPin);
      digitalWrite(ledRojoPin, LOW);
      digitalWrite(ledVerdePin, HIGH);

      // Indicar transmisión
      parpadeoAmarillo();
    }
    else {
      
      // Indicar transmisión
      parpadeoAmarillo();
    }
    // Otros comandos se ignoran
  }

  // Actualizar el sonido de la sirena (si está activa)
  actualizarSirena();
}
