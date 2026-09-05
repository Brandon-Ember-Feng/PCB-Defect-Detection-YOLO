/*************************************************
 * 第1步诊断：只初始化+清屏，不写任何字符
 * 用途：判断LCD初始化命令是否真正被屏接收
 *
 * 正确现象：背光点亮，但两行都干干净净、没有任何黑块/字符
 *   -> 若两行干净 = 初始化成功，硬件没问题，回去显示字符即可
 *   -> 若仍有一行/整屏黑块 = 初始化没传进去，是屏接触/硬件问题
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

void lcd_write_cmd(uchar cmd)
{
    LCD_RS = 0; LCD_RW = 0;
    LCD_DATA = cmd; delay_ms(2);
    LCD_EN = 1;   delay_ms(2);
    LCD_EN = 0;   delay_ms(2);
}

void main(void)
{
    digital_tube_off();
    delay_ms(100);
    LCD_RS = 0; LCD_RW = 0;
    LCD_DATA = 0x38; LCD_EN=1; delay_ms(5); LCD_EN=0; delay_ms(8);
    LCD_DATA = 0x38; LCD_EN=1; delay_ms(5); LCD_EN=0; delay_ms(8);
    LCD_DATA = 0x38; LCD_EN=1; delay_ms(5); LCD_EN=0; delay_ms(8);
    lcd_write_cmd(0x38);
    lcd_write_cmd(0x08);
    lcd_write_cmd(0x01); delay_ms(8);  // 清屏
    lcd_write_cmd(0x06);
    lcd_write_cmd(0x0c);              // 开显示、无光标、无字符所以应全空白
    while(1);
}
