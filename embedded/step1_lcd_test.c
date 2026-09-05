/*************************************************
 * 第1步 v4：LCD1602 点亮（ZY-1 开发板，纯延时稳定版）
 * 硬件：STC89C52RC + 11.0592MHz
 *   RS=P1.0  RW=P1.1  E=P2.5  D0~D7=P0 ; 数码管DU=P2.6 WE=P2.7
 *
 * v4：去掉忙检测(读P0会和数码管锁存冲突导致死机)，
 *     全部用固定延时，每条命令后延时给足，绝不死循环
 * 现象：第一行 1111111111111111，第二行 2222222222222222
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

/* 11.0592MHz 约1ms */
void delay_ms(uint ms)
{
    uint i, j;
    for(i = ms; i > 0; i--)
        for(j = 114; j > 0; j--);
}

/* 关闭数码管，释放共用P0 */
void digital_tube_off(void)
{
    P0 = 0x00; DU = 1; DU = 0;
    P0 = 0x00; WE = 1; WE = 0;
}

/* 写命令：纯延时，不读P0 */
void lcd_write_cmd(uchar cmd)
{
    LCD_RS = 0;
    LCD_RW = 0;
    LCD_DATA = cmd;
    delay_ms(2);
    LCD_EN = 1;
    delay_ms(2);
    LCD_EN = 0;
    delay_ms(2);
}

/* 写数据 */
void lcd_write_data(uchar dat)
{
    LCD_RS = 1;
    LCD_RW = 0;
    LCD_DATA = dat;
    delay_ms(2);
    LCD_EN = 1;
    delay_ms(2);
    LCD_EN = 0;
    delay_ms(2);
}

/* 标准HD44780初始化（全程固定延时） */
void lcd_init(void)
{
    delay_ms(100);
    LCD_RS = 0; LCD_RW = 0;
    LCD_DATA = 0x38; LCD_EN=1; delay_ms(5); LCD_EN=0; delay_ms(8);
    LCD_DATA = 0x38; LCD_EN=1; delay_ms(5); LCD_EN=0; delay_ms(8);
    LCD_DATA = 0x38; LCD_EN=1; delay_ms(5); LCD_EN=0; delay_ms(8);
    lcd_write_cmd(0x38);  // 8位、2行、5x7
    lcd_write_cmd(0x08);  // 显示关
    lcd_write_cmd(0x01); delay_ms(8);  // 清屏，多等
    lcd_write_cmd(0x06);  // 光标右移
    lcd_write_cmd(0x0c);  // 显示开、无光标
}

void lcd_show_string(uchar row, uchar col, uchar *str)
{
    lcd_write_cmd((row == 0 ? 0x80 : 0xC0) + col);
    while(*str)
        lcd_write_data(*str++);
}

void main(void)
{
    digital_tube_off();
    lcd_init();
    lcd_show_string(0, 0, "1111111111111111");
    lcd_show_string(1, 0, "2222222222222222");
    while(1);
}
