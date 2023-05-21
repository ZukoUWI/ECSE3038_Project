#include <Arduino.h>
#include <Wifi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>

//Stores Credentials
#include "env.h"


//Initializing Fan, Led & PIR sensor pins
#define fanPin 22
#define lightPin 23
#define pirPin 24 

//API endpoint in headerfile
const char* apiEndpoint = api_url;

// Random temperature generator between 20 - 36
float getTemp(){
  return random(20.2,36.0);
}


// Random presence generated for PIR sensor used to detect motion
bool getPIR(){
  return random(0,1);
}

void setup() {
	pinMode(fanPin,OUTPUT);
  pinMode(lightPin,OUTPUT);

  Serial.begin(9600);

	// Connect to Wi-Fi network using the USERNAME and PASSWORD from the env.h file
  WiFi.begin(WIFI_USER, WIFI_PASS);
  Serial.println("Connecting to WiFi");

  //Prints "." every 0.5 seconds until connected
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  //Prints Connected with IP Address once connection is established
  Serial.println("");
  Serial.println("Connected to WiFi network with IP Address: ");
  Serial.println(WiFi.localIP());
}

void loop() {
  //Check WiFi connection status
  if(WiFi.status()== WL_CONNECTED){
    Serial.println("");
    HTTPClient http;
  
    //url for info
    String url = "https://" + String(apiEndpoint) + "/info";
    http.begin(url);
    http.addHeader("Content-type", "application/json");

    //Setting document size for PUT
    StaticJsonDocument<1024> docput;
    String httpRequestData;
    docput["temperature"] = getTemp();
    docput["presence"] = getPIR();
  

    //Setting document size for PUT
    serializeJson(docput, httpRequestData);

    //HTTP PUT request
    int httpResponseCode = http.POST(httpRequestData);
    String http_response;

    //HTTP response codes if statements
    if (httpResponseCode>0) {
      Serial.print("HTTP Response code: ");
      Serial.println(httpResponseCode);

      Serial.print("HTTP Response from server: ");
      http_response = http.getString();
      Serial.println(http_response);
    }
    else {
      Serial.print("Error code: ");
      Serial.println(httpResponseCode);
    }

    http.end();

    //Convert to url for state
    url = "https://" + String(apiEndpoint) + "/state";  
    //Establish Connection with server for GET request    
    http.begin(url);
    httpResponseCode = http.GET();
    
    //HTTP response codes if statements
    if (httpResponseCode>0) {
        Serial.print("HTTP Response code: ");
        Serial.println(httpResponseCode);

        Serial.print("Response from server: ");
        http_response = http.getString();
        Serial.println(http_response);
      }
      else {
        Serial.print("Error code: ");
        Serial.println(httpResponseCode);
    }
 
    //Setting document size for GET
    StaticJsonDocument<1024> docget;
    DeserializationError error = deserializeJson(docget, http_response);

    if (error) {
      Serial.print("deserializeJson() failed: ");
      Serial.println(error.c_str());
      return;
    }
    
    bool temp = docget["fan"]; 
    bool light= docget["light"]; 
    bool presence= docget["presence"]; 

    digitalWrite(fanPin,temp);
    digitalWrite(lightPin,light);
    digitalWrite(pirPin,presence);
    
    //End connection to the server
    http.end();
  }
  //Otherwise print Wifi disconnected if connection terminates
  else {
    Serial.println("WiFi Disconnected");
  }
}





