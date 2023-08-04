//int ledpin1 = 5;
//int ledpin2 = 6;
//int ledpin3 = 7;

String usercmd = "";

void setup() {
  // put your setup code here, to run once:
  
  Serial.begin(9600); //baudrate
//  Serial.setTimeout(1); //100ms
  pinMode(5, OUTPUT);
  pinMode(6, OUTPUT);
  pinMode(7, OUTPUT);
  digitalWrite(5, LOW); //initialise low (lights off)
  digitalWrite(6, LOW);
  digitalWrite(7, LOW);
  pinMode(LED_BUILTIN, OUTPUT);
  digitalWrite(LED_BUILTIN, LOW);
  
}

void loop() {
  // put your main code here, to run repeatedly:
  while (Serial.available()){ 
    
    usercmd = Serial.readStringUntil('\n');

    
    if(usercmd == "11"){
      digitalWrite(5, HIGH);
      digitalWrite(LED_BUILTIN, HIGH);
      }
    if(usercmd == "10"){
      digitalWrite(5, LOW);
      digitalWrite(LED_BUILTIN, LOW);
      }
    if(usercmd == "21"){
      digitalWrite(6, HIGH);
      }
    if(usercmd == "20"){
      digitalWrite(6, LOW);
      }
    if(usercmd == "31"){
      digitalWrite(7, HIGH);
      }
    if(usercmd == "30"){
      digitalWrite(7, LOW);
      }
    }
}
