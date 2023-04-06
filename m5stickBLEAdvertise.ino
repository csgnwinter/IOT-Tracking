#include <M5StickCPlus.h>
#include <BLEDevice.h>

BLEServer* pServer = NULL;
BLEService* pService = NULL;

void setup() {
  M5.begin();

  BLEDevice::init("MyBluetoothDevice"); // specify the Bluetooth service name
  pServer = BLEDevice::createServer();
  pService = pServer->createService("4fafc201-1fb5-459e-8fcc-c5c9c331914b"); // specify the UUID of the service
  pService->start();

  BLEAdvertising* pAdvertising = BLEDevice::getAdvertising();
  pAdvertising->addServiceUUID(pService->getUUID()); // add the UUID of the service
  pAdvertising->setScanResponse(true);
  pAdvertising->setMinPreferred(0x06);
  pAdvertising->setMinPreferred(0x12);
  BLEDevice::startAdvertising();
}

void loop() {
  // do nothing
}