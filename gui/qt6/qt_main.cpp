// ЕОМ «Київ»: Qt 6 Widgets demonstration frontend.
// Persistent C++ CPU backend, versioned tab-separated protocol (v1).
// No dependency on Tkinter/Python, Qt Designer, QML, or generated moc files.
#include <QApplication>
#include <QCheckBox>
#include <QComboBox>
#include <QDir>
#include <QFileDialog>
#include <QFileInfo>
#include <QFontDatabase>
#include <QFrame>
#include <QGridLayout>
#include <QGroupBox>
#include <QHeaderView>
#include <QLabel>
#include <QMainWindow>
#include <QLineEdit>
#include <QMessageBox>
#include <QMap>
#include <QShortcut>
#include <QFont>
#include <QPainter>
#include <QPaintEvent>
#include <QPlainTextEdit>
#include <QProcess>
#include <QPushButton>
#include <QQueue>
#include <QScrollBar>
#include <QSpinBox>
#include <QSplitter>
#include <QStatusBar>
#include <QTabWidget>
#include <QTableWidget>
#include <QTimer>
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QWidget>
#include <QRegularExpression>

#include <algorithm>
#include <cstdint>
#include <utility>
#include <limits>

namespace {
QString octal(quint64 value, int width) {
    return QString::number(value, 8).rightJustified(width, QLatin1Char('0'));
}
bool parseOct(const QString& input, int width, quint64 max, quint64& out) {
    const auto s = input.trimmed();
    if (s.size() != width) return false;
    for (QChar ch : s) if (ch < QLatin1Char('0') || ch > QLatin1Char('7')) return false;
    bool ok=false;
    out = s.toULongLong(&ok,8);
    return ok && out <= max;
}
void alert(QWidget* parent, const QString& message) {
    QMessageBox::warning(parent, QString::fromUtf8("ЕОМ «Київ»"), message);
}
QString buttonStyle() {
    return QStringLiteral("QPushButton {padding: 7px 12px; border-radius: 5px; border: 1px solid #526174; background:#283442;} "
           "QPushButton:hover{background:#344659;} QPushButton:disabled{color:#7b8999;border-color:#313b46;} "
           "QPushButton:pressed{background:#455b72;}");
}

class LampPanel final : public QWidget {
    quint64 command_ = 0;
    quint64 c_=0,a_=0,p_=0,loop_=0;
    bool stopped_=false;
public:
    explicit LampPanel(QWidget* parent=nullptr) : QWidget(parent) {
        setMinimumHeight(222);
        setSizePolicy(QSizePolicy::Expanding,QSizePolicy::Fixed);
    }
    void setState(quint64 k,quint64 c,quint64 a,quint64 p,quint64 loop,bool t) {
        command_=k;c_=c;a_=a;p_=p;loop_=loop;stopped_=t;update();
    }
protected:
    void paintEvent(QPaintEvent*) override {
        QPainter painter(this);
        painter.setRenderHint(QPainter::Antialiasing,true);
        painter.fillRect(rect(),QColor("#18212a"));
        painter.setPen(QColor("#8294a6"));
        painter.drawRoundedRect(rect().adjusted(1,1,-2,-2),8,8);
        painter.setFont(QFont(QStringLiteral("Consolas"),9));
        const struct Row { const char* name; int bits; quint64 word; int y; } rows[] = {
            {"K   41",41,command_,34}, {"C   11",11,c_,74},
            {"A   10",10,a_,110}, {"P   11",11,p_,146},
            {"Cy  10",10,loop_,182}
        };
        const int origin=95;
        const double step=std::min(19.0, std::max(7.6,(width()-origin-48.0)/41.0));
        for (const auto& row : rows) {
            painter.setPen(QColor("#b6c7d7"));
            painter.drawText(12,row.y+4,QString::fromLatin1(row.name));
            for (int j=0;j<row.bits;++j) {
                const int bit=row.bits-1-j;
                const bool on=(row.word>>bit)&1u;
                const QPointF at(origin + j*step, row.y);
                painter.setPen(QPen(on?QColor("#ebc878"):QColor("#485664"),1));
                painter.setBrush(on?QColor("#efba5b"):QColor("#29343e"));
                painter.drawEllipse(at,4.6,4.6);
            }
        }
        painter.setPen(QColor("#c4d0dd"));
        painter.drawText(width()-100,184,QStringLiteral("T"));
        painter.setPen(stopped_?QColor("#ff7777"):QColor("#56705a"));
        painter.setBrush(stopped_?QColor("#d85252"):QColor("#355b47"));
        painter.drawEllipse(QPointF(width()-68,178),7,7);
    }
};

class MainWindow final : public QMainWindow {
    struct Request {QString kind;QString line;};
    QProcess backend_;
    QByteArray readBuffer_;
    QQueue<Request> requests_;
    Request inFlight_;
    bool busy_=false, ready_=false, loaded_=false, running_=false, faulted_=false;
    QString root_, rom_, image_;
    quint64 command_=0,c_=0,a_=0,p_=0,loop_=0,batchCount_=0;
    bool t_=false;
    int memStart_=0;

    QLineEdit *imageEdit_=nullptr,*startEdit_=nullptr,*memoryEdit_=nullptr,*nkWord_=nullptr;
    QComboBox *demo_=nullptr,*nkAddr_=nullptr,*speed_=nullptr;
    QSpinBox *limit_=nullptr;
    QPushButton *load_=nullptr,*step_=nullptr,*run_=nullptr,*pause_=nullptr,*reset_=nullptr,*save_=nullptr,*restore_=nullptr,*setNk_=nullptr,*clearNk_=nullptr;
    QLabel *status_=nullptr,*regC_=nullptr,*regK_=nullptr,*regA_=nullptr,*regP_=nullptr,*regLoop_=nullptr,*regT_=nullptr,*steps_=nullptr,*imageInfo_=nullptr;
    LampPanel *lamps_=nullptr;
    QTableWidget *memoryTable_=nullptr;
    QPlainTextEdit *traceArea_=nullptr;
    QTimer runTimer_;

    static QGroupBox* group(const QString& title,QWidget* parent=nullptr) {
        auto* g=new QGroupBox(title,parent);
        return g;
    }
    static QLabel* infoLabel(const QString& initial={}) {
        auto* l=new QLabel(initial);
        l->setTextInteractionFlags(Qt::TextSelectableByMouse);
        return l;
    }
    void addRegisters(QGridLayout* grid, int row, int col, const QString& name, QLabel*& value) {
        auto* label=new QLabel(name);
        label->setStyleSheet(QStringLiteral("color:#95aabc"));
        value=infoLabel(QStringLiteral("—"));
        QFont f=QFontDatabase::systemFont(QFontDatabase::FixedFont);
        f.setPointSize(10);
        value->setFont(f);
        grid->addWidget(label,row,col);
        grid->addWidget(value,row,col+1);
    }
    void setStatus(const QString& s) {
        status_->setText(s);
        statusBar()->showMessage(s);
    }
    QString repoFile(const QString& suffix) const {return QDir(root_).absoluteFilePath(suffix);}
    void makeUI() {
        setWindowTitle(QString::fromUtf8("ЕОМ «Київ» — Qt 6 · демонстраційний GUI"));
        resize(1190,830);
        setMinimumSize(860,650);
        setStyleSheet(QStringLiteral("QMainWindow,QWidget{background:#1b2530;color:#e2ebf3;} "
            "QGroupBox{border:1px solid #435366;border-radius:7px;margin-top:13px;padding-top:10px;font-weight:600;}"
            "QGroupBox::title{subcontrol-origin:margin;left:13px;padding:0 5px;} "
            "QLineEdit,QPlainTextEdit,QTableWidget,QComboBox,QSpinBox{background:#111b25;color:#e0eaf3;border:1px solid #47586b;border-radius:4px;padding:4px;} "
            "QTabWidget::pane{border:1px solid #435366;} QTabBar::tab{background:#253341;color:#dae6f0;padding:7px 14px;} "
            "QTabBar::tab:selected{background:#3c5268;} QHeaderView::section{background:#263546;color:#dae6f0;padding:5px;}"));
        QWidget* center = new QWidget;
        setCentralWidget(center);
        auto* outer=new QVBoxLayout(center);
        outer->setSpacing(9);
        auto* top=new QHBoxLayout;
        demo_=new QComboBox;
        demo_->addItem(QString::fromUtf8("H9 · додавання з −0"),QStringLiteral("examples/historical/gy1962/au1_addition_0143_0150.k41|0143"));
        demo_->addItem(QString::fromUtf8("H23 · нормалізація"),QStringLiteral("examples/historical/gy1962/au1_batch38_0300_0345.k41|0302"));
        top->addWidget(new QLabel(QString::fromUtf8("Приклад:")));
        top->addWidget(demo_,1);
        auto* choose=new QPushButton(QString::fromUtf8("Обрати файл…"));
        top->addWidget(choose);
        top->addWidget(new QLabel(QString::fromUtf8("Старт:")));
        startEdit_=new QLineEdit(QStringLiteral("0143"));startEdit_->setMaximumWidth(64);
        top->addWidget(startEdit_);
        load_=new QPushButton(QString::fromUtf8("Завантажити"));top->addWidget(load_);
        outer->addLayout(top);

        auto* imageRow=new QHBoxLayout;
        imageEdit_=new QLineEdit;
        imageEdit_->setReadOnly(true);
        imageRow->addWidget(new QLabel(QString::fromUtf8("Образ:")));
        imageRow->addWidget(imageEdit_,1);
        imageInfo_=infoLabel(QString::fromUtf8("Не завантажено"));imageRow->addWidget(imageInfo_);
        outer->addLayout(imageRow);

        auto* controls=new QHBoxLayout;
        step_=new QPushButton(QString::fromUtf8("Крок  F5"));
        run_=new QPushButton(QString::fromUtf8("Пуск  F6"));
        pause_=new QPushButton(QString::fromUtf8("Пауза  F7"));
        reset_=new QPushButton(QString::fromUtf8("Перезавантажити"));
        save_=new QPushButton(QString::fromUtf8("Запам’ятати стан"));
        restore_=new QPushButton(QString::fromUtf8("Відновити стан"));
        for(auto* b:{step_,run_,pause_,reset_,save_,restore_,load_,choose}) b->setStyleSheet(buttonStyle());
        controls->addWidget(step_);controls->addWidget(run_);controls->addWidget(pause_);
        controls->addWidget(reset_);
        controls->addWidget(save_);controls->addWidget(restore_);
        controls->addStretch();
        controls->addWidget(new QLabel(QString::fromUtf8("Команд/пакет:")));
        limit_=new QSpinBox;limit_->setRange(1,32);limit_->setValue(16);limit_->setMaximumWidth(62);controls->addWidget(limit_);
        controls->addWidget(new QLabel(QString::fromUtf8("Темп:")));
        speed_=new QComboBox;
        speed_->addItem(QString::fromUtf8("Повільно"),300);
        speed_->addItem(QString::fromUtf8("Звичайно"),90);
        speed_->addItem(QString::fromUtf8("Швидко"),25);
        speed_->setCurrentIndex(1);
        controls->addWidget(speed_);
        outer->addLayout(controls);

        QSplitter* split=new QSplitter(Qt::Vertical);
        outer->addWidget(split,1);
        QWidget* upper=new QWidget;auto* upperLayout=new QVBoxLayout(upper);
        upperLayout->setContentsMargins(0,0,0,0);
        auto* regs=group(QString::fromUtf8("Регістри процесора"));
        auto* registerGrid=new QGridLayout(regs);
        addRegisters(registerGrid,0,0,QStringLiteral("C"),regC_);
        addRegisters(registerGrid,0,2,QStringLiteral("K"),regK_);
        addRegisters(registerGrid,0,4,QStringLiteral("A"),regA_);
        addRegisters(registerGrid,1,0,QStringLiteral("P"),regP_);
        addRegisters(registerGrid,1,2,QString::fromUtf8("Ц"),regLoop_);
        addRegisters(registerGrid,1,4,QStringLiteral("T"),regT_);
        addRegisters(registerGrid,2,0,QString::fromUtf8("Виконано"),steps_);
        upperLayout->addWidget(regs);
        auto* lampGroup=group(QString::fromUtf8("Індикатори — функціональне представлення"));
        auto* lampLayout=new QVBoxLayout(lampGroup);
        lamps_=new LampPanel;
        lampLayout->addWidget(lamps_);
        upperLayout->addWidget(lampGroup);
        split->addWidget(upper);

        auto* tabs=new QTabWidget;
        QWidget* memoryPage=new QWidget;auto* memLayout=new QVBoxLayout(memoryPage);
        auto* memBar=new QHBoxLayout;
        memBar->addWidget(new QLabel(QString::fromUtf8("Початкова адреса (вісімкова):")));
        memoryEdit_=new QLineEdit(QStringLiteral("0000"));memoryEdit_->setMaximumWidth(72);memBar->addWidget(memoryEdit_);
        auto* refresh=new QPushButton(QString::fromUtf8("Оновити пам’ять"));refresh->setStyleSheet(buttonStyle());memBar->addWidget(refresh);memBar->addStretch();
        memLayout->addLayout(memBar);
        memoryTable_=new QTableWidget(32,2);
        memoryTable_->setHorizontalHeaderLabels({QString::fromUtf8("Адреса"),QString::fromUtf8("41-бітове слово")});
        memoryTable_->horizontalHeader()->setStretchLastSection(true);
        memoryTable_->verticalHeader()->setVisible(false);
        memoryTable_->setEditTriggers(QAbstractItemView::NoEditTriggers);
        memoryTable_->setSelectionBehavior(QAbstractItemView::SelectRows);
        memoryTable_->setAlternatingRowColors(true);
        memoryTable_->setColumnWidth(0,130);
        for(int i=0;i<32;i++) {
            memoryTable_->setItem(i,0,new QTableWidgetItem(octal(i,4)));
            memoryTable_->setItem(i,1,new QTableWidgetItem(QStringLiteral("—")));
        }
        memLayout->addWidget(memoryTable_);
        tabs->addTab(memoryPage,QString::fromUtf8("Пам’ять"));
        QWidget* tracePage=new QWidget;auto* traceLayout=new QVBoxLayout(tracePage);
        traceArea_=new QPlainTextEdit;traceArea_->setReadOnly(true);
        traceArea_->setMaximumBlockCount(1200);
        traceArea_->setPlaceholderText(QString::fromUtf8("Адреси виконаних команд з’являться тут."));
        traceLayout->addWidget(traceArea_);
        tabs->addTab(tracePage,QString::fromUtf8("Трасування"));
        QWidget* nkPage=new QWidget;auto* nkLayout=new QVBoxLayout(nkPage);
        auto* nkRow=new QHBoxLayout;
        nkAddr_=new QComboBox;nkAddr_->addItems({QStringLiteral("3000"),QStringLiteral("3001"),QStringLiteral("3002")});
        nkWord_=new QLineEdit(QStringLiteral("00000000000000"));nkWord_->setMaxLength(14);nkWord_->setMinimumWidth(175);
        setNk_=new QPushButton(QString::fromUtf8("Вибрати слово пульта"));
        clearNk_=new QPushButton(QString::fromUtf8("Повернути джерело «шафа»"));
        setNk_->setStyleSheet(buttonStyle());clearNk_->setStyleSheet(buttonStyle());
        nkRow->addWidget(new QLabel(QString::fromUtf8("НК:")));nkRow->addWidget(nkAddr_);
        nkRow->addWidget(new QLabel(QString::fromUtf8("41-бітове слово:")));nkRow->addWidget(nkWord_);
        nkRow->addWidget(setNk_);nkRow->addWidget(clearNk_);nkLayout->addLayout(nkRow);
        nkLayout->addWidget(new QLabel(QString::fromUtf8("Джерело «пульт» підтримано для НК 3000–3002. Інші комірки НК тут не змінюються.")));
        nkLayout->addStretch();
        tabs->addTab(nkPage,QString::fromUtf8("НК / пульт"));
        split->addWidget(tabs);
        split->setStretchFactor(0,2);split->setStretchFactor(1,2);
        status_=infoLabel(QString::fromUtf8("Запуск backend…"));outer->addWidget(status_);

        connect(demo_,QOverload<int>::of(&QComboBox::currentIndexChanged),this,[this](int idx){
            Q_UNUSED(idx);
            const QStringList parts=demo_->currentData().toString().split('|');
            if(parts.size()==2){image_=repoFile(parts[0]);imageEdit_->setText(image_);startEdit_->setText(parts[1]);}
        });
        connect(choose,&QPushButton::clicked,this,[this]{
            const QString name=QFileDialog::getOpenFileName(this,QString::fromUtf8("Обрати образ «Києва»"),root_,QStringLiteral("KYIV41 (*.k41);;All files (*)"));
            if(!name.isEmpty()) {image_=name;imageEdit_->setText(name);}
        });
        connect(load_,&QPushButton::clicked,this,[this]{loadImage();});
        connect(step_,&QPushButton::clicked,this,[this]{running_=false;updateButtons();enqueue({"STEP",QStringLiteral("STEP\t1")});});
        connect(run_,&QPushButton::clicked,this,[this]{running_=true;updateButtons();setStatus(QString::fromUtf8("Автоматичне виконання"));});
        connect(pause_,&QPushButton::clicked,this,[this]{
            running_=false;updateButtons();setStatus(QString::fromUtf8("Пауза між пакетами команд"));
            if(!busy_&&requests_.isEmpty())refreshMemory();
        });
        connect(reset_,&QPushButton::clicked,this,[this]{loadImage();});
        connect(save_,&QPushButton::clicked,this,[this]{enqueue({"SAVE","SAVE"});});
        connect(restore_,&QPushButton::clicked,this,[this]{running_=false;updateButtons();enqueue({"RESTORE","RESTORE"});});
        connect(refresh,&QPushButton::clicked,this,[this]{refreshMemory();});
        connect(setNk_,&QPushButton::clicked,this,[this]{
            quint64 word=0;
            if(!parseOct(nkWord_->text(),14,(quint64(1)<<41)-1,word)) {alert(this,QString::fromUtf8("Потрібне 41-бітове слово у форматі 14 вісімкових цифр."));return;}
            enqueue({"SETNK",QStringLiteral("SETNK\t%1\t%2").arg(nkAddr_->currentText(),octal(word,14))});
        });
        connect(clearNk_,&QPushButton::clicked,this,[this]{enqueue({"CLEARNK",QStringLiteral("CLEARNK\t%1").arg(nkAddr_->currentText())});});
        connect(&runTimer_,&QTimer::timeout,this,[this]{
            if(running_ && ready_ && loaded_ && !busy_ && requests_.isEmpty() && backend_.state()==QProcess::Running)
                enqueue({"STEP",QStringLiteral("STEP\t%1").arg(limit_->value())});
        });
        connect(speed_,QOverload<int>::of(&QComboBox::currentIndexChanged),this,[this](int){
            runTimer_.setInterval(speed_->currentData().toInt());
        });
        runTimer_.start(speed_->currentData().toInt());
        auto* f5=new QShortcut(QKeySequence(Qt::Key_F5),this);
        auto* f6=new QShortcut(QKeySequence(Qt::Key_F6),this);
        auto* f7=new QShortcut(QKeySequence(Qt::Key_F7),this);
        connect(f5,&QShortcut::activated,step_,&QPushButton::click);
        connect(f6,&QShortcut::activated,run_,&QPushButton::click);
        connect(f7,&QShortcut::activated,pause_,&QPushButton::click);
        demo_->setCurrentIndex(-1);demo_->setCurrentIndex(0);
        updateButtons();
    }
    void updateButtons(){
        const bool active=ready_&&loaded_&&!faulted_;
        load_->setEnabled(ready_);
        step_->setEnabled(active&&!running_&&!t_);
        run_->setEnabled(active&&!running_&&!t_);
        pause_->setEnabled(active&&running_);
        reset_->setEnabled(ready_&&loaded_);
        save_->setEnabled(active);restore_->setEnabled(active);
        setNk_->setEnabled(active);clearNk_->setEnabled(active);
    }
    void enqueue(Request r) {
        if(backend_.state()!=QProcess::Running) {setStatus(QString::fromUtf8("Backend недоступний"));return;}
        requests_.enqueue(std::move(r));pump();
    }
    void pump() {
        if(!ready_||busy_||requests_.isEmpty()||backend_.state()!=QProcess::Running) return;
        inFlight_=requests_.dequeue();busy_=true;
        QByteArray bytes=inFlight_.line.toUtf8();bytes.append('\n');
        if(backend_.write(bytes)!=bytes.size()) {
            busy_=false;running_=false;faulted_=true;setStatus(QString::fromUtf8("Помилка передавання команди backend"));updateButtons();
        }
    }
    void loadImage() {
        running_=false;batchCount_=0;
        quint64 start=0;
        if(!parseOct(startEdit_->text(),4,03777,start)||start==0) {alert(this,QString::fromUtf8("Старт має містити 4 вісімкові цифри та допустиму адресу."));return;}
        if(image_.isEmpty()||!QFileInfo::exists(image_)) {alert(this,QString::fromUtf8("Файл образу не знайдено."));return;}
        if(image_.contains('\t')||image_.contains('\r')||image_.contains('\n')) {alert(this,QString::fromUtf8("Неприпустимі символи в шляху."));return;}
        requests_.clear();
        enqueue({"LOAD",QStringLiteral("LOAD\t%1\t%2").arg(QFileInfo(image_).absoluteFilePath(),octal(start,4))});
        updateButtons();
    }
    void refreshMemory(){
        quint64 address=0;
        if(!parseOct(memoryEdit_->text(),4,03777,address)||address+32>04000) {alert(this,QString::fromUtf8("Початкова адреса має дозволяти читання 32 слів."));return;}
        memStart_=int(address);
        enqueue({"DUMP",QStringLiteral("DUMP\t%1\t32").arg(octal(address,4))});
    }
    void applyState(const QStringList& fields) {
        QMap<QString,QString> map;
        for(const auto& field:fields){
            const int pos=field.indexOf('=');if(pos>0)map[field.left(pos)]=field.mid(pos+1);
        }
        if(!map.contains("C"))return;
        regC_->setText(map.value("C"));regK_->setText(map.value("K"));regA_->setText(map.value("A"));
        regP_->setText(map.value("P"));regLoop_->setText(map.value("LOOP"));regT_->setText(map.value("T"));
        steps_->setText(map.value("STEPS"));
        parseOct(map.value("C"),4,03777,c_);parseOct(map.value("K"),14,(quint64(1)<<41)-1,command_);
        parseOct(map.value("A"),4,03777,a_);parseOct(map.value("P"),4,03777,p_);parseOct(map.value("LOOP"),4,03777,loop_);
        t_=map.value("T")=="1";
        lamps_->setState(command_,c_,a_,p_,loop_,t_);
        if(t_)running_=false;
        updateButtons();
    }
    void backendResponse(const QString& line) {
        const QStringList fields=line.split('\t');
        if(fields.isEmpty())return;
        if(inFlight_.kind=="PING") {
            if(fields.size()<3||fields[0]!="OK"||fields[1]!="PING"||!line.contains("PROTOCOL=1")){
                fatal(QString::fromUtf8("Несумісна версія протоколу backend: ")+line);return;
            }
            busy_=false;ready_=true;setStatus(QString::fromUtf8("Backend готовий, ROM перевірено"));updateButtons();pump();return;
        }
        if(fields[0]=="ERR") {
            busy_=false;running_=false;
            setStatus(QString::fromUtf8("Помилка CPU: ")+fields.mid(1).join(' '));
            updateButtons();pump();return;
        }
        if(fields[0]!="OK"||fields.size()<2||fields[1]!=inFlight_.kind) {
            fatal(QString::fromUtf8("Неочікувана відповідь backend: ")+line);return;
        }
        const QString kind=inFlight_.kind;
        busy_=false;
        if(kind=="LOAD") {
            loaded_=true;faulted_=false;traceArea_->clear();traceArea_->appendPlainText(QString::fromUtf8("Завантажено: ")+image_);
            imageInfo_->setText(fields.size()>2?fields[2]:QString::fromUtf8("Завантажено"));
            applyState(fields.mid(2));
            setStatus(QString::fromUtf8("Образ завантажено"));
            requests_.enqueue({"DUMP",QStringLiteral("DUMP\t%1\t32").arg(octal(memStart_,4))});
        } else if(kind=="STEP") {
            ++batchCount_;
            QString path;
            for(const auto& field:fields)if(field.startsWith("PATH="))path=field.mid(5);
            if(!path.isEmpty()&&path!="-") {
                const QStringList pcs=path.split(',');
                for(const auto& pc:pcs)traceArea_->appendPlainText(pc);
            }
            applyState(fields.mid(2));
            if(t_)setStatus(QString::fromUtf8("CPU зупинено командою STOP"));
            if(!running_||t_||batchCount_%12==0)requests_.enqueue({"DUMP",QStringLiteral("DUMP\t%1\t32").arg(octal(memStart_,4))});
        } else if(kind=="DUMP") {
            QString data, start;
            for(const auto& field:fields){if(field.startsWith("DATA="))data=field.mid(5);if(field.startsWith("START="))start=field.mid(6);}
            bool ok=false;const int base=start.toInt(&ok,8);
            const QStringList words=data.split(',');
            if(!ok||words.size()!=32) {fatal(QString::fromUtf8("Некоректна відповідь пам’яті"));return;}
            for(int i=0;i<32;i++) {
                memoryTable_->item(i,0)->setText(octal(base+i,4));
                memoryTable_->item(i,1)->setText(words[i]);
            }
        } else if(kind=="RESTORE") {
            applyState(fields.mid(2));setStatus(QString::fromUtf8("Стан відновлено"));
            requests_.enqueue({"DUMP",QStringLiteral("DUMP\t%1\t32").arg(octal(memStart_,4))});
            traceArea_->appendPlainText(QString::fromUtf8("— відновлено checkpoint —"));
        } else if(kind=="SAVE") {setStatus(QString::fromUtf8("Checkpoint запам’ятано в процесі"));}
        else if(kind=="SETNK"||kind=="CLEARNK") {setStatus(QString::fromUtf8("НК оновлено: ")+fields.mid(2).join(" "));}
        updateButtons();pump();
    }
    void fatal(const QString& detail){
        running_=false;ready_=false;faulted_=true;requests_.clear();busy_=false;
        setStatus(detail);updateButtons();
        alert(this,detail);
    }
    void startBackend() {
        const QString exe=QDir(QCoreApplication::applicationDirPath()).absoluteFilePath(
#ifdef Q_OS_WIN
            QStringLiteral("kyiv_gui_backend.exe")
#else
            QStringLiteral("kyiv_gui_backend")
#endif
        );
        if(!QFileInfo::exists(exe)){fatal(QString::fromUtf8("Не знайдено backend: ")+exe);return;}
        backend_.setProgram(exe);
        backend_.setArguments({rom_});
        backend_.setWorkingDirectory(root_);
        backend_.setProcessChannelMode(QProcess::SeparateChannels);
        connect(&backend_,&QProcess::started,this,[this]{
            busy_=true;inFlight_={"PING","PING"};backend_.write("PING\n");
        });
        connect(&backend_,&QProcess::readyReadStandardOutput,this,[this]{
            readBuffer_+=backend_.readAllStandardOutput();
            if(readBuffer_.size()>262144){fatal(QString::fromUtf8("Завелика відповідь backend"));return;}
            while(true){
                const int eol=readBuffer_.indexOf('\n');if(eol<0)break;
                QByteArray line=readBuffer_.left(eol);readBuffer_.remove(0,eol+1);
                if(line.endsWith('\r'))line.chop(1);
                if(line.isEmpty())continue;
                backendResponse(QString::fromUtf8(line));
            }
        });
        connect(&backend_,&QProcess::readyReadStandardError,this,[this]{
            const QString err=QString::fromLocal8Bit(backend_.readAllStandardError()).trimmed();
            if(!err.isEmpty())setStatus(QString::fromUtf8("Backend stderr: ")+err.left(300));
        });
        connect(&backend_,&QProcess::errorOccurred,this,[this](QProcess::ProcessError){
            if(backend_.state()==QProcess::NotRunning)fatal(QString::fromUtf8("Backend не запустився: ")+backend_.errorString());
        });
        connect(&backend_,QOverload<int,QProcess::ExitStatus>::of(&QProcess::finished),this,[this](int code,QProcess::ExitStatus){
            running_=false;ready_=false;loaded_=false;
            setStatus(QString::fromUtf8("Backend завершився, код ")+QString::number(code));updateButtons();
        });
        backend_.start();
    }
public:
    explicit MainWindow(QString root,QString rom,QWidget* parent=nullptr) : QMainWindow(parent),root_(std::move(root)),rom_(std::move(rom)){
        makeUI();startBackend();
    }
    ~MainWindow() override {
        runTimer_.stop();
        if(backend_.state()==QProcess::Running){
            backend_.write("QUIT\n");backend_.closeWriteChannel();
            if(!backend_.waitForFinished(1200))backend_.kill();
        }
    }
};
} // anonymous namespace

int main(int argc,char** argv) {
    QApplication app(argc,argv);
    const QStringList args=app.arguments();
    if(args.size()!=3) {
        QMessageBox::critical(nullptr,QString::fromUtf8("ЕОМ «Київ»"),
            QString::fromUtf8("Запуск: kyiv_gui_qt6 <корінь репозиторію> <ROM.txt>"));
        return 2;
    }
    const QString root=QDir(args[1]).absolutePath();
    const QString rom=QFileInfo(args[2]).absoluteFilePath();
    if(!QFileInfo(root+QStringLiteral("/inc/kyiv.h")).isFile()||!QFileInfo(rom).isFile()){
        QMessageBox::critical(nullptr,QString::fromUtf8("ЕОМ «Київ»"),QString::fromUtf8("Неправильний шлях до репозиторію або ROM."));
        return 2;
    }
    MainWindow window(root,rom);
    window.show();
    return app.exec();
}
