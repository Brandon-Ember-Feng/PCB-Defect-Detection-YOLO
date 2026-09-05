/*************************************************
 * 第3步：缺陷数据帧解析 + LCD分类轮播显示
 * 硬件：STC89C52RC + 11.0592MHz，板载CH340 + LCD1602
 *
 * ★ 通信协议（定长帧）★
 *   帧头'$' + 6组两位数量 + 帧尾'#'，共14字节
 *   6组顺序固定：
 *     [0]鼠咬MB  [1]缺孔MH  [2]毛刺SP
 *     [3]短路SH  [4]开路OC  [5]多余铜SC
 *   例：$030100020000# 表示 鼠咬3 缺孔1 毛刺0 短路2 开路0 多余铜0
 *
 * LCD显示：
 *   第一行常驻：Defect Total:NN（缺陷总数）
 *   第二行每1.5秒轮播一页，每页3类：
 *     页0: MB03 MH01 SP00
 *     页1: SH02 OC00 SC00
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

/* 6类缺陷数量 + 缩写表 */
uchar cnt[6] = {0,0,0,0,0,0};
uchar code NAME[6][3] = {"MB","MH","SP","SH","OC","SC"};  // 存在ROM省RAM

/* 串口接收状态机 */
#define S_HEAD 0
#define S_DATA 1
uchar  rx_state = S_HEAD;
uchar  rx_idx = 0;
uchar  rx_raw[12];
volatile bit new_frame = 0;

/* 轮播节拍 */
volatile unsigned long tick_ms = 0;
unsigned long last_toggle = 0;
uchar page = 0;

/* ---------- 延时/LCD ---------- */
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
    LCD_RS = 0; LCD_RW = 0; LCD_DATA = cmd;
    delay_ms(1); LCD_EN = 1; delay_ms(1); LCD_EN = 0; delay_ms(1);
}
void lcd_write_data(uchar dat)
{
    LCD_RS = 1; LCD_RW = 0; LCD_DATA = dat;
    delay_ms(1); LCD_EN = 1; delay_ms(1); LCD_EN = 0; delay_ms(1);
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
    lcd_write_cmd(0x01); delay_ms(5);
    lcd_write_cmd(0x06);
    lcd_write_cmd(0x0c);
}
void lcd_show_string(uchar row, uchar col, uchar *str)
{
    lcd_write_cmd((row == 0 ? 0x80 : 0xC0) + col);
    while(*str)
        lcd_write_data(*str++);
}

/* 把0~99数字转成两位字符写入buf（buf至少3字节） */
void num2str(uchar n, uchar *buf)
{
    buf[0] = n/10 + '0';
    buf[1] = n%10 + '0';
    buf[2] = '\0';
}

/* ---------- 定时器0：1ms节拍，用于轮播 ---------- */
void timer0_init(void)
{
    TMOD &= 0xF0; TMOD |= 0x01;   // T0方式1
    TH0 = 0xFC; TL0 = 0x66;       // 11.0592约1ms
    ET0 = 1; TR0 = 1;
    EA = 1;
}
void timer0_isr(void) interrupt 1
{
    TH0 = 0xFC; TL0 = 0x66;
    tick_ms++;
}

/* ---------- 串口 9600 ---------- */
void uart_init(void)
{
    TMOD &= 0x0F; TMOD |= 0x20;   // T1方式2（与T0共存，TMOD合并设置）
    TH1 = 0xFD; TL1 = 0xFD;
    TR1 = 1;
    SCON = 0x50;
    PCON &= 0x7F;
    ES = 1; EA = 1;
}
/* 串口中断：状态机收帧 */
void uart_isr(void) interrupt 4
{
    uchar ch;
    if(RI)
    {
        RI = 0;
        ch = SBUF;
        SBUF = ch; while(!TI); TI = 0;   // 回显，便于调试
        switch(rx_state)
        {
            case S_HEAD:
                if(ch == '$'){ rx_idx = 0; rx_state = S_DATA; }
                break;
            case S_DATA:
                if(ch == '#')
                {
                    if(rx_idx == 12) new_frame = 1;   // 正好12位才成帧
                    rx_state = S_HEAD;
                }
                else if(ch >= '0' && ch <= '9' && rx_idx < 12)
                {
                    rx_raw[rx_idx++] = ch;
                }
                else
                {
                    rx_state = S_HEAD;   // 非法字符，重新等帧头
                }
                break;
        }
    }
}

/* 解析一帧：12位字符 -> 6个数量 */
void parse_frame(void)
{
    uchar i;
    for(i = 0; i < 6; i++)
        cnt[i] = (rx_raw[i*2]-'0')*10 + (rx_raw[i*2+1]-'0');
}

/* 刷新第一行：缺陷总数 */
void show_total(void)
{
    uchar buf[3], line[17], total = 0, p = 0, i;
    uchar code head[] = "Defect Total:";
    for(i = 0; i < 6; i++) total += cnt[i];
    for(i = 0; head[i]; i++) line[p++] = head[i];
    num2str(total, buf);
    line[p++] = buf[0]; line[p++] = buf[1];
    while(p < 16) line[p++] = ' ';
    line[16] = '\0';
    lcd_show_string(0, 0, line);
}

/* 刷新第二行：当前页3类，格式 MB03 MH01 SP00 */
void show_page(void)
{
    uchar line[17], p = 0, k, base, numbuf[3];
    base = page * 3;
    for(k = 0; k < 3; k++)
    {
        line[p++] = NAME[base+k][0];
        line[p++] = NAME[base+k][1];
        num2str(cnt[base+k], numbuf);
        line[p++] = numbuf[0];
        line[p++] = numbuf[1];
        if(k < 2) line[p++] = ' ';
    }
    while(p < 16) line[p++] = ' ';
    line[16] = '\0';
    lcd_show_string(1, 0, line);
}

void main(void)
{
    digital_tube_off();
    lcd_init();
    timer0_init();
    uart_init();
    lcd_show_string(0, 0, "PCB Detect Sys ");
    lcd_show_string(1, 0, "Waiting Frame..");

    while(1)
    {
        if(new_frame)
        {
            ES = 0; new_frame = 0; ES = 1;
            parse_frame();
            show_total();
            page = 0;
            show_page();
            last_toggle = tick_ms;
        }
        /* 每1.5秒翻页 */
        if(tick_ms - last_toggle >= 1500)
        {
            last_toggle = tick_ms;
            page ^= 1;
            show_page();
        }
    }
}
