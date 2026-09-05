/*************************************************
 * 最终界面：PCB检测状态机 + NG多缺陷轮播（ZY-1 / STC89C52RC / 11.0592）
 *   LCD RS=P1.0 RW=P1.1 E=P2.5 数据=P0 ; 数码管DU=P2.6 WE=P2.7
 *   串口 P3.0=RXD P3.1=TXD 9600
 *
 * 界面（第一行固定 PCB INSPECTION）：
 *   待机  第二行 SYSTEM READY
 *   检测中      CHECKING...
 *   合格        PASS
 *   不合格      NG <类别> <置信度>% ，多个缺陷每1.5秒轮播
 *
 * 通信协议：
 *   $W#                 待机
 *   $C#                 检测中
 *   $P#                 合格
 *   $N;3:93;0:85#       不合格：类别号:置信度(0-99)，分号分隔多个
 *     类别号 0鼠咬 1毛刺 2缺孔 3短路 4开路 5多余铜
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

/* ====== 红绿灯（共阳：输出0点亮，1熄灭） ======
   绿灯=板载L2(P1.2)；红灯=P1.4(板载为黄灯L4，可外接红LED到J4的P1.4)
   板载红灯L0/L1的P1.0/P1.1已被LCD占用，故红灯用P1.4 */
sbit LED_GREEN = P1^2;
sbit LED_RED   = P1^4;
#define LED_ON   0
#define LED_OFF  1

/* 系统状态 */
#define ST_WAIT  0
#define ST_CHECK 1
#define ST_PASS  2
#define ST_NG    3
uchar sys_state = ST_WAIT;

/* 缺陷项：类别+置信度，最多6项 */
typedef struct { uchar cls; uchar conf; } Defect;
Defect def_list[6];
uchar def_cnt = 0;
uchar page = 0;

/* 类别缩写（<=6字符，保证 "NG XXX 99%" 不超16列）
   顺序与模型一致：0鼠咬 1毛刺 2缺孔 3短路 4开路 5多余铜 */
uchar code *code NAME[6] = {"MBITE","SPUR","MHOLE","SHORT","OPEN","SCOP"};

/* 串口解析 */
volatile bit new_cmd = 0;
uchar  req_state = ST_WAIT;       // 待应用状态
Defect tmp_def[6];
uchar  tmp_cnt = 0;
uchar  parse_field = 0;           // 0:读类别 1:读置信度十位 2:置信度个位
uchar  conf_ten = 0;

/* 轮播节拍 */
volatile unsigned long tick_ms = 0;
unsigned long last_toggle = 0;
unsigned long last_blink = 0;
uchar red_blink = 0;

/* ---------------- 延时/LCD ---------------- */
void delay_ms(uint ms){ uint i,j; for(i=ms;i>0;i--) for(j=114;j>0;j--); }
void digital_tube_off(void){ P0=0x00;DU=1;DU=0; P0=0x00;WE=1;WE=0; }
void lcd_cmd(uchar c){ LCD_RS=0;LCD_RW=0;LCD_DATA=c;delay_ms(1);LCD_EN=1;delay_ms(1);LCD_EN=0;delay_ms(1); }
void lcd_dat(uchar c){ LCD_RS=1;LCD_RW=0;LCD_DATA=c;delay_ms(1);LCD_EN=1;delay_ms(1);LCD_EN=0;delay_ms(1); }
void lcd_init(void)
{
    delay_ms(100); LCD_RS=0;LCD_RW=0;
    LCD_DATA=0x38;LCD_EN=1;delay_ms(5);LCD_EN=0;delay_ms(8);
    LCD_DATA=0x38;LCD_EN=1;delay_ms(5);LCD_EN=0;delay_ms(8);
    LCD_DATA=0x38;LCD_EN=1;delay_ms(5);LCD_EN=0;delay_ms(8);
    lcd_cmd(0x38); lcd_cmd(0x08); lcd_cmd(0x01);delay_ms(5); lcd_cmd(0x06); lcd_cmd(0x0c);
}
void lcd_str(uchar row, uchar col, uchar *s)
{
    lcd_cmd((row==0?0x80:0xC0)+col);
    while(*s) lcd_dat(*s++);
}
/* 第二行写16字符定长串（不足补空格，防止残留） */
void line2(uchar *s)
{
    uchar i=0;
    lcd_cmd(0xC0);
    while(s[i] && i<16){ lcd_dat(s[i]); i++; }
    while(i<16){ lcd_dat(' '); i++; }
}

/* ---------------- 定时器0 1ms ---------------- */
void timer0_init(void){ TMOD&=0xF0;TMOD|=0x01; TH0=0xFC;TL0=0x66; ET0=1;TR0=1; EA=1; }
void timer0_isr(void) interrupt 1 { TH0=0xFC;TL0=0x66; tick_ms++; }

/* ---------------- 串口 9600 ---------------- */
void uart_init(void){ TMOD&=0x0F;TMOD|=0x20; TH1=0xFD;TL1=0xFD; TR1=1; SCON=0x50; PCON&=0x7F; ES=1;EA=1; }
void uart_isr(void) interrupt 4
{
    uchar ch;
    if(!RI) return;
    RI=0; ch=SBUF;
    SBUF=ch; while(!TI); TI=0;       // 回显便于调试

    if(ch=='$'){ tmp_cnt=0; parse_field=0; return; }   // 帧头：重置
    if(ch=='#'){ new_cmd=1; return; }                  // 帧尾：提交

    if(parse_field==0 && (ch=='W'||ch=='C'||ch=='P'||ch=='N'))
    {
        req_state = (ch=='W'?ST_WAIT : ch=='C'?ST_CHECK : ch=='P'?ST_PASS : ST_NG);
        return;
    }
    if(req_state!=ST_NG) return;      // 只有NG帧才解析缺陷列表

    if(ch==';'){                     // 新缺陷项
        if(tmp_cnt<6){ tmp_def[tmp_cnt].cls=0; tmp_def[tmp_cnt].conf=0; tmp_cnt++; }
        parse_field=0; return;
    }
    if(ch==':'){ parse_field=1; return; }
    if(ch>='0'&&ch<='9' && tmp_cnt>0)
    {
        uchar d=ch-'0';
        if(parse_field==0) tmp_def[tmp_cnt-1].cls=d;        // 类别号
        else if(parse_field==1){ conf_ten=d; parse_field=2; }
        else { tmp_def[tmp_cnt-1].conf=conf_ten*10+d; parse_field=0; } // 置信度两位
    }
}

/* ---------------- 界面刷新 ---------------- */
void show_ng_page(void)
{
    uchar line[17], i=0, c, n;
    uchar code *nm;
    if(def_cnt==0){ line2("NG              "); return; }
    line[i++]='N'; line[i++]='G'; line[i++]=' ';
    c = def_list[page].cls;
    if(c<6)
    {
        nm = NAME[c];
        while(*nm && i<16) line[i++]=*nm++;
    }
    line[i++]=' ';
    n = def_list[page].conf;
    line[i++]=(n/10)+'0'; line[i++]=(n%10)+'0'; line[i++]='%';
    line[i]='\0';
    line2(line);
}
void apply_command(void)
{
    uchar i;
    ES=0; new_cmd=0; ES=1;
    sys_state=req_state;
    if(sys_state==ST_NG)
    {
        for(i=0;i<tmp_cnt && i<6;i++) def_list[i]=tmp_def[i];
        def_cnt=(tmp_cnt>6?6:tmp_cnt);
        page=0;
    }
    lcd_str(0,0,"PCB INSPECTION  ");     // 第一行固定
    switch(sys_state)
    {
        case ST_WAIT:  line2("SYSTEM READY    "); break;
        case ST_CHECK: line2("CHECKING...     "); break;
        case ST_PASS:  line2("PASS            "); break;
        case ST_NG:    show_ng_page(); break;
    }
    /* 红绿灯：PASS绿灯常亮，NG红灯(闪烁在主循环)，其余全灭 */
    LED_GREEN = (sys_state==ST_PASS) ? LED_ON : LED_OFF;
    LED_RED   = LED_OFF;                 // NG闪烁由主循环控制，先熄灭
    red_blink = 0;
    last_toggle=tick_ms;
}

void main(void)
{
    digital_tube_off();
    lcd_init();
    timer0_init();
    uart_init();
    sys_state=ST_WAIT;
    LED_GREEN=LED_OFF; LED_RED=LED_OFF;   // 开机两灯灭
    lcd_str(0,0,"PCB INSPECTION  ");
    line2("SYSTEM READY    ");

    while(1)
    {
        if(new_cmd) apply_command();
        /* NG状态下每1.5秒轮播一个缺陷 */
        if(sys_state==ST_NG && def_cnt>1 && tick_ms-last_toggle>=1500)
        {
            last_toggle=tick_ms;
            page++;
            if(page>=def_cnt) page=0;
            show_ng_page();
        }
        /* NG状态红灯每0.5秒闪烁，其余状态保持熄灭 */
        if(sys_state==ST_NG)
        {
            if(tick_ms-last_blink>=500)
            {
                last_blink=tick_ms;
                red_blink^=1;
                LED_RED = red_blink ? LED_ON : LED_OFF;
            }
        }
    }
}
