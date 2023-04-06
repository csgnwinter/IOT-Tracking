#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include "btlib.h"
#include <bluetooth/bluetooth.h>
#include <bluetooth/hci.h>
#include <bluetooth/hci_lib.h>

int main()
  {
    char endo_jw[] = "4C:75:25:CB:83:46";

    if(init_blue("devices.txt") == 0)
      return(0);

    printf("Mesh created\n");
    //RSSI stuff
    int dev_id = hci_get_route(NULL);
    int sock = hci_open_dev(dev_id);
    hci_le_set_scan_parameters(sock, 0x01, htobs(0x0010), htobs(0x0010), 0x00, $
    hci_le_set_scan_enable(sock, 0x01, 1, 1000);

    struct hci_filter nf, of;
    hci_filter_clear(&nf);
    hci_filter_set_ptype(HCI_EVENT_PKT, &nf);
    hci_filter_set_event(EVT_LE_META_EVENT, &nf);
    setsockopt(sock, SOL_HCI, HCI_FILTER, &nf, sizeof(nf));

    while(1) {
        unsigned char buf[HCI_MAX_EVENT_SIZE], *ptr;
        int len;

        len = read(sock, buf, sizeof(buf));
        ptr = buf + (1 + HCI_EVENT_HDR_SIZE);
        len -= (1 + HCI_EVENT_HDR_SIZE);

        evt_le_meta_event *meta = (evt_le_meta_event *) ptr;
        if(meta->subevent != 0x02) continue;

        le_advertising_info *info = (le_advertising_info *) (meta->data + 1);
        int rssi = (char)info->data[info->length];
        char addr[18];
        ba2str(&(info->bdaddr), addr);
        //printf("Device %s\n", addr);


        char dataBuf[32];
        if(strcmp(addr,endo_jw) == 0) {
            sprintf(dataBuf,"0:%d",(rssi*-1)+120);
            printf("Device endo_jw has RSSI %d\n", (rssi*-1)+120);
            // broadcast mesh packet
            write_mesh(dataBuf, strlen(dataBuf));
            evt_le_meta_event *meta = (evt_le_meta_event *) ptr;
        if(meta->subevent != 0x02) continue;

        le_advertising_info *info = (le_advertising_info *) (meta->data + 1);
        int rssi = (char)info->data[info->length];
        char addr[18];
        ba2str(&(info->bdaddr), addr);
        //printf("Device %s\n", addr);


        char dataBuf[32];
        if(strcmp(addr,endo_jw) == 0) {
            sprintf(dataBuf,"0:%d",(rssi*-1)+120);
            printf("Device endo_jw has RSSI %d\n", (rssi*-1)+120);
            // broadcast mesh packet
            write_mesh(dataBuf, strlen(dataBuf));
            // sleep(3);
        }
    }
    close(sock);
}
