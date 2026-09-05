/*************************************************
 * 第2步 v3：串口回环（整帧接收，解决字符被覆盖问题）
 * 硬件：STC89C52RC + 11.0592MHz，板载CH340
 *   串口 P3.0=RXD P3.1=TXD ；LCD RS=P1.0 RW=P1.1 E=P2.5 数据=P0
 *
 * 帧规则：一帧以 '#' 或 回车/换行 结尾，收到帧尾才整帧刷新LCD
 *   电脑发送：RX:OK#   -> LCD第二行完整显示 RX:OK，同时电脑收到逐字符回显
 *   缓冲区收满16字节也会自动成帧
 *************************************************/
#include <reg52.h>
#define uchar unsigned char
#define uint  unsigned int

sbit LCD_RS = P1^0;
sbit LCD_RW = P1^1;
sbit LCD_EN = P2^5;
#define LCD_DATA P0
sbit DU = P2^6;
sbit WE = P2^7;

#define RX_BUF_LEN 17
uchar rx_buf[RX_BUF_LEN];
volatile uchar rx_len = 0;
volatile bit   rx_frame = 0;      // 一帧完整接收标志

void delay_ms(uint ms)
{
    uint i, j;
    for(i = ms; i > 0; i--)
        for(j = 114; j > 0; j--);
}

void digital_tube_off(void)
{
    P0 = 0x00; DU = 1; DU = 0;
    P0 = 0x00; WE = 1; WE = 0;
}

/* ---------- LCD驱动 ---------- */
void lcd_write_cmd(uchar cmd)
{
    LCD_RS = 0; LCD_RW = 0; LCD_DATA = cmd;
    delay_ms(2); LCD_EN = 1; delay_ms(2); LCD_EN = 0; delay_ms(2);
}
void lcd_write_data(uchar dat)
{
    LCD_RS = 1; LCD_RW = 0; LCD_DATA = dat;
    delay_ms(2); LCD_EN = 1; delay_ms(2); LCD_EN = 0; delay_ms(2);
}
void lcd_init(void)
{
    delay_ms(100);
    LCD_RS = 0; LCD_RW = 0;
    LCD_DATA = 0x38; LCD_EN=1; delay_ms(5); LCD_EN=0; delay_ms(8);
    LCD_DATA = 0x38; LCD_EN=1; delay_ms(5); LCD_EN=0; delay_ms(8);
    LCD_DATA = 0x38; LCD_EN=1; delay_ms(5); LCD_EN=0; delay_ms(8);
    lcd_write_cmd(0x38);
    lcd_write_cmd(0x08);
    lcd_write_cmd(0x01); delay_ms(8);
    lcd_write_cmd(0x06);
    lcd_write_cmd(0x0c);
}
void lcd_show_string(uchar row, uchar col, uchar *str)
{
    lcd_write_cmd((row == 0 ? 0x80 : 0xC0) + col);
    while(*str)
        lcd_write_data(*str++);
}

/* ---------- 串口 9600 ---------- */
void uart_init(void)
{
    TMOD &= 0x0F; TMOD |= 0x20;
    TH1 = 0xFD; TL1 = 0xFD;
    TR1 = 1;
    SCON = 0x50;
    PCON &= 0x7F;
    EA = 1; ES = 1;
}

/* ---------- 串口中断：逐字节接收+回显，帧尾成帧 ---------- */
void uart_isr(void) interrupt 4
{
    uchar ch;
    if(RI)
    {
        RI = 0;
        ch = SBUF;
        SBUF = ch; while(!TI); TI = 0;    // 回显
        /* 帧尾：# 或 回车 或 换行 */
        if(ch == '#' || ch == '\r' || ch == '\n')
        {
            if(rx_len > 0)
            {
                rx_buf[rx_len] = '\0';
                rx_frame = 1;             // 一帧完整
            }
        }
        else if(rx_len < RX_BUF_LEN - 1)
        {
            rx_buf[rx_len++] = ch;
            if(rx_len >= RX_BUF_LEN - 1)  // 缓冲满也成帧
            {
                rx_buf[rx_len] = '\0';
                rx_frame = 1;
            }
        }
    }
}

void main(void)
{
    uchar disp[RX_BUF_LEN];
    uchar i, len;

    digital_tube_off();
    lcd_init();
    uart_init();
    lcd_show_string(0, 0, "UART Frame Test");
    lcd_show_string(1, 0, "                ");

    while(1)
    {
        if(rx_frame)
        {
            ES = 0;
            len = rx_len;
            for(i = 0; i < len; i++) disp[i] = rx_buf[i];
            disp[len] = '\0';
            rx_len = 0;
            rx_buf[0] = '\0';
            rx_frame = 0;
            ES = 1;

            lcd_show_string(1, 0, "                ");
            lcd_show_string(1, 0, disp);
        }
    }
}
