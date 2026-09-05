/*************************************************
 * 第0步：心跳验证（不涉及LCD，专门确认程序是否真的在运行）
 * 现象：板上 P1 口的 L1~L8 流水灯持续同时闪烁（约每秒一次）
 *       数码管保持熄灭
 *
 * ✅ 如果LED在闪烁 = 烧录/运行正常，问题在LCD代码，继续排查LCD
 * ❌ 如果LED完全不亮/不闪 = 程序没烧进去或芯片没运行，先解决烧录
 *************************************************/
#include <reg52.h>
#define uchar unsigned char
#define uint  unsigned int

sbit DU = P2^6;   // 数码管段选锁存
sbit WE = P2^7;   // 数码管位选锁存

/* 粗略延时，11.0592MHz 下约 ms 毫秒 */
void delay_ms(uint ms)
{
    uint i, j;
    for(i = ms; i > 0; i--)
        for(j = 110; j > 0; j--);
}

void main(void)
{
    /* 先熄灭数码管 */
    P0 = 0x00; DU = 1; DU = 0;
    P0 = 0x00; WE = 1; WE = 0;

    while(1)
    {
        P1 = 0x00;        // P1全部输出0 -> L1~L8亮
        delay_ms(500);
        P1 = 0xFF;        // P1全部输出1 -> L1~L8灭
        delay_ms(500);
    }
}
