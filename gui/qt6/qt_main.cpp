// ЕОМ «Київ»: Qt 6 Widgets demonstration frontend.
// Persistent C++ CPU backend, versioned tab-separated protocol (v1).
// No dependency on Tkinter/Python, Qt Designer, QML, or generated moc files.
#include <QApplication>
#include <QCryptographicHash>
#include <QFile>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QSignalBlocker>
#include <QTemporaryDir>
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
#include <memory>

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
    bool t_=false, fpDone_=false;
    QString selectedRunMode_=QStringLiteral("image"), selectedEndPointer_;
    QString loadedRunMode_=QStringLiteral("image");
    int memStart_=0;

    QLineEdit *imageEdit_=nullptr,*startEdit_=nullptr,*memoryEdit_=nullptr,*nkWord_=nullptr;
    QComboBox *demo_=nullptr,*nkAddr_=nullptr,*speed_=nullptr,*romSets_=nullptr,*operatorSelect_=nullptr;
    QLabel *romSource_=nullptr, *runModeLabel_=nullptr;
    QPushButton *operatorReplay_=nullptr;
    QString activeScenarioId_, activeBackendSet_;
    std::unique_ptr<QTemporaryDir> preparedRom_;
    // H118: validated C2a oracle, checked in this very GUI backend session.
    QJsonObject pendingOracle_, loadedOracle_;
    QStringList oracleWatchAddresses_;
    bool oracleAuditing_=false, oracleFinished_=false, oracleEligible_=true;
    int oracleWatchIndex_=0;
    quint64 actualSteps_=0, fpDispatches_=0;
    // H118: C2b actions use the SAME persistent backend that drives the lamps.
    QJsonArray operatorActions_;
    bool operatorActive_=false, operatorWaitingLoad_=false;
    int operatorIndex_=0;
    QString operatorId_;
    QSpinBox *limit_=nullptr;
    QPushButton *load_=nullptr,*step_=nullptr,*run_=nullptr,*pause_=nullptr,*reset_=nullptr,*save_=nullptr,*restore_=nullptr,*setNk_=nullptr,*clearNk_=nullptr;
    QLabel *status_=nullptr,*regC_=nullptr,*regK_=nullptr,*regA_=nullptr,*regP_=nullptr,*regLoop_=nullptr,*regT_=nullptr,*steps_=nullptr,*imageInfo_=nullptr;
    QLabel *fpDispatchLabel_=nullptr,*regFpDispatches_=nullptr;
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
    // UI-only indicator: the backend owns the counter; the C2a manifest owns
    // its expected value. A terminal END_POINTER visit is counted by H115.
    void updateFpDispatches() {
        if(!fpDispatchLabel_ || !regFpDispatches_)return;
        const bool visible=loaded_ && loadedRunMode_==QStringLiteral("fp-image");
        fpDispatchLabel_->setVisible(visible);
        regFpDispatches_->setVisible(visible);
        if(!visible)return;
        const auto expected=loadedOracle_.value(QStringLiteral("dispatches"));
        const QString actual=QString::number(fpDispatches_);
        if(expected.isDouble() && expected.toInt(-1)>=0)
            regFpDispatches_->setText(actual+QStringLiteral(" / ")+QString::number(expected.toInt()));
        else
            regFpDispatches_->setText(actual+QString::fromUtf8(" / —"));
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
        auto* catalogRow=new QHBoxLayout;
        catalogRow->addWidget(new QLabel(QString::fromUtf8("Змінна ПЗП:")));
        romSets_=new QComboBox;romSets_->addItem(QString::fromUtf8("Лише ROM.txt"),QString());
        catalogRow->addWidget(romSets_,1);
        auto* refreshCatalog=new QPushButton(QString::fromUtf8("Оновити каталог"));
        catalogRow->addWidget(refreshCatalog);
        romSource_=infoLabel(QString::fromUtf8("ROM.txt · без змінного блока"));
        catalogRow->addWidget(romSource_,2);
        outer->addLayout(catalogRow);
        auto* operatorRow=new QHBoxLayout;
        operatorRow->addWidget(new QLabel(QString::fromUtf8("Сценарій оператора:")));
        operatorSelect_=new QComboBox;
        operatorSelect_->addItem(QString::fromUtf8("— обрати C2b сценарій —"), QString());
        operatorRow->addWidget(operatorSelect_,1);
        auto* operatorRefresh=new QPushButton(QString::fromUtf8("Оновити C2b"));
        operatorRow->addWidget(operatorRefresh);
        operatorReplay_=new QPushButton(QString::fromUtf8("Відтворити й перевірити"));
        operatorReplay_->setStyleSheet(buttonStyle());
        operatorRow->addWidget(operatorReplay_);
        outer->addLayout(operatorRow);
        runModeLabel_=infoLabel(QString::fromUtf8("Режим: машинні команди CPU"));
        outer->addWidget(runModeLabel_);

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
        fpDispatchLabel_=new QLabel(QString::fromUtf8("Дисп. МП"));
        fpDispatchLabel_->setStyleSheet(QStringLiteral("color:#95aabc"));
        regFpDispatches_=infoLabel(QStringLiteral("0 / —"));
        regFpDispatches_->setFont(QFontDatabase::systemFont(QFontDatabase::FixedFont));
        const QString hint=QString::fromUtf8("Відвідування диспетчера МП (PC=3305), включно з межею END_POINTER; фактичне / очікуване");
        fpDispatchLabel_->setToolTip(hint);
        regFpDispatches_->setToolTip(hint);
        registerGrid->addWidget(fpDispatchLabel_,2,2);
        registerGrid->addWidget(regFpDispatches_,2,3);
        fpDispatchLabel_->hide();regFpDispatches_->hide();
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
            if(parts.size()>=2){
                image_=repoFile(parts[0]);imageEdit_->setText(image_);startEdit_->setText(parts[1]);
                const bool scenario=(parts.size()==6 && !parts[3].startsWith(QStringLiteral("dual_")));
                activeScenarioId_=scenario?parts[3]:QString();
                selectedRunMode_=(parts.size()==6)?parts[4]:QStringLiteral("image");
                selectedEndPointer_=(parts.size()==6)?parts[5]:QString();
                const QString set=(parts.size()>=4)?parts[2]:QString();
                const int index=romSets_->findData(set);
                if(index>=0)romSets_->setCurrentIndex(index);
                runModeLabel_->setText(selectedRunMode_==QStringLiteral("fp-image")
                    ?QString::fromUtf8("Режим: FP-команди через програмну МП на CPU «Києва»")
                    :QString::fromUtf8("Режим: пряме виконання машинних команд CPU"));
            }
        });
        connect(choose,&QPushButton::clicked,this,[this]{
            const QString name=QFileDialog::getOpenFileName(this,QString::fromUtf8("Обрати образ «Києва»"),root_,QStringLiteral("KYIV41 (*.k41);;All files (*)"));
            if(!name.isEmpty()) {
                activeScenarioId_.clear();selectedRunMode_=QStringLiteral("image");selectedEndPointer_.clear();
                demo_->setCurrentIndex(-1);image_=name;imageEdit_->setText(name);
                runModeLabel_->setText(QString::fromUtf8("Режим: пряме виконання машинних команд CPU"));
            }
        });
        connect(load_,&QPushButton::clicked,this,[this]{loadImage();});
        connect(refreshCatalog,&QPushButton::clicked,this,[this]{populateCatalog();});
        connect(operatorRefresh,&QPushButton::clicked,this,[this]{populateOperators();});
        connect(operatorReplay_,&QPushButton::clicked,this,[this]{startOperatorReplay();});
        connect(operatorSelect_,QOverload<int>::of(&QComboBox::currentIndexChanged),this,[this](int){updateButtons();});
        connect(romSets_,QOverload<int>::of(&QComboBox::currentIndexChanged),this,[this](int i){
            romSource_->setText(i>=0?romSets_->itemData(i,Qt::UserRole+1).toString():QString());
        });
        connect(step_,&QPushButton::clicked,this,[this]{running_=false;updateButtons();enqueue({"STEP",QStringLiteral("STEP\t1")});});
        connect(run_,&QPushButton::clicked,this,[this]{running_=true;updateButtons();setStatus(QString::fromUtf8("Автоматичне виконання"));});
        connect(pause_,&QPushButton::clicked,this,[this]{
            running_=false;updateButtons();setStatus(QString::fromUtf8("Пауза між пакетами команд"));
            if(!busy_&&requests_.isEmpty())refreshMemory();
        });
        connect(reset_,&QPushButton::clicked,this,[this]{loadImage();});
        connect(save_,&QPushButton::clicked,this,[this]{invalidateOracle();enqueue({"SAVE","SAVE"});});
        connect(restore_,&QPushButton::clicked,this,[this]{invalidateOracle();running_=false;updateButtons();enqueue({"RESTORE","RESTORE"});});
        connect(refresh,&QPushButton::clicked,this,[this]{refreshMemory();});
        connect(setNk_,&QPushButton::clicked,this,[this]{
            quint64 word=0;
            if(!parseOct(nkWord_->text(),14,(quint64(1)<<41)-1,word)) {alert(this,QString::fromUtf8("Потрібне 41-бітове слово у форматі 14 вісімкових цифр."));return;}
            invalidateOracle();
            enqueue({"SETNK",QStringLiteral("SETNK\t%1\t%2").arg(nkAddr_->currentText(),octal(word,14))});
        });
        connect(clearNk_,&QPushButton::clicked,this,[this]{invalidateOracle();enqueue({"CLEARNK",QStringLiteral("CLEARNK\t%1").arg(nkAddr_->currentText())});});
        connect(&runTimer_,&QTimer::timeout,this,[this]{
            if(running_ && ready_ && loaded_ && !fpDone_ && !t_ && !busy_ && requests_.isEmpty() && backend_.state()==QProcess::Running){
                int count=limit_->value();
                if(!loadedOracle_.isEmpty() && !oracleFinished_ && oracleEligible_){
                    const qint64 remaining=loadedOracle_.value(QStringLiteral("max_steps")).toInt()-qint64(actualSteps_);
                    if(remaining<=0){running_=false;oracleHold(QStringLiteral("STEP_LIMIT"));return;}
                    count=std::min(count,int(remaining));
                }
                enqueue({"STEP",QStringLiteral("STEP\t%1").arg(count)});
            }
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
        const bool active=ready_&&loaded_&&!faulted_&&!operatorActive_;
        load_->setEnabled(ready_&&!operatorActive_);
        if(operatorReplay_)operatorReplay_->setEnabled(ready_&&!operatorActive_&&!running_&&!busy_&&
                  operatorSelect_&&!operatorSelect_->currentData().toString().isEmpty());
        step_->setEnabled(active&&!running_&&!t_&&!fpDone_);
        run_->setEnabled(active&&!running_&&!t_&&!fpDone_);
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
    // Run the existing C1a/C2a validators through a bounded, shell-free process.
    bool catalogCall(const QStringList& command,QJsonObject& result,QString& error) {
        const QString tool=repoFile(QStringLiteral("tools/historical/qt_rom_browser_v1.py"));
        if(!QFileInfo(tool).isFile()){error=QString::fromUtf8("Не знайдено Qt ROM bridge");return false;}
        QProcess process;
        process.setWorkingDirectory(root_);
        process.start(QStringLiteral("python"),QStringList{QStringLiteral("-B"),tool,
                       QStringLiteral("--repo"),root_}+command);
        if(!process.waitForStarted(4000)){
            error=QString::fromUtf8("Python не запустився: ")+process.errorString();return false;
        }
        if(!process.waitForFinished(30000)){
            process.kill();process.waitForFinished(1000);
            error=QString::fromUtf8("Тайм-аут підготовки ROM-каталогу");return false;
        }
        const auto output=process.readAllStandardOutput();
        const auto diagnostic=process.readAllStandardError();
        if(process.exitStatus()!=QProcess::NormalExit||process.exitCode()!=0||output.size()>131072){
            error=QString::fromUtf8(diagnostic.left(450));return false;
        }
        QJsonParseError parseError;
        const auto doc=QJsonDocument::fromJson(output,&parseError);
        if(parseError.error!=QJsonParseError::NoError||!doc.isObject()){
            error=QString::fromUtf8("Некоректна JSON-відповідь каталогу");return false;
        }
        result=doc.object();
        if(!result.value(QStringLiteral("status")).toString().startsWith(QStringLiteral("PASS_H116_H1_"))){
            error=QString::fromUtf8("Валідація ROM-каталогу не пройдена");return false;
        }
        return true;
    }
    void populateCatalog(){
        QJsonObject report;QString error;
        if(!catalogCall({QStringLiteral("list")},report,error)){
            setStatus(QString::fromUtf8("ROM-каталог недоступний: ")+error);
            return;  // Preserve the old, already validated selections.
        }
        const QString previous=romSets_->currentData().toString();
        const QString demoPrevious=demo_->currentData().toString();
        QSignalBlocker pauseRom(romSets_),pauseDemo(demo_);
        romSets_->clear();
        romSets_->addItem(QString::fromUtf8("Лише ROM.txt"),QString());
        romSets_->setItemData(0,QString::fromUtf8("ROM.txt · без змінного блока"),Qt::UserRole+1);
        for(const auto value:report.value(QStringLiteral("sets")).toArray()){
            const auto item=value.toObject();
            const QString id=item.value(QStringLiteral("id")).toString();
            const QString info=item.value(QStringLiteral("provenance")).toString()+
                QString::fromUtf8(" · невідомих слів: ")+
                QString::number(item.value(QStringLiteral("unknown")).toInt());
            romSets_->addItem(id,id);
            const int n=romSets_->count()-1;
            romSets_->setItemData(n,info,Qt::UserRole+1);
            romSets_->setItemData(n,item.value(QStringLiteral("description")).toString(),Qt::ToolTipRole);
        }
        const int index=romSets_->findData(previous);
        romSets_->setCurrentIndex(index<0?0:index);
        romSource_->setText(romSets_->currentData(Qt::UserRole+1).toString());
        while(demo_->count()>2)demo_->removeItem(2);
        for(const auto value:report.value(QStringLiteral("scenarios")).toArray()){
            const auto item=value.toObject();
            const QString id=item.value(QStringLiteral("id")).toString();
            const QString data=item.value(QStringLiteral("program")).toString()+"|"+
                item.value(QStringLiteral("entry")).toString()+"|"+
                item.value(QStringLiteral("rom_set")).toString()+"|"+id+"|"+
                item.value(QStringLiteral("mode")).toString()+"|"+
                item.value(QStringLiteral("end_pointer")).toString();
            demo_->addItem(QString::fromUtf8("Сценарій · ")+id,data);
            demo_->setItemData(demo_->count()-1,
                item.value(QStringLiteral("origin")).toString()+"\n"+
                item.value(QStringLiteral("description")).toString(),Qt::ToolTipRole);
        }
        // H116 Dual Euler: one pinned 38-word image, two routes through the same Kyiv CPU.
        const QString dual=QStringLiteral("examples/dual_euler_reconstructed/EULER_DUAL_MODE.k41");
        demo_->addItem(QString::fromUtf8("Dual Euler · CPU (експеримент)"),
                       dual+QStringLiteral("|0200||dual_cpu|image|"));
        demo_->addItem(QString::fromUtf8("Dual Euler · МП (експеримент)"),
                       dual+QStringLiteral("|0210|fp_functional|dual_fp|fp-image|0236"));
        const int d=demo_->findData(demoPrevious);
        if(d>=0)demo_->setCurrentIndex(d);
        else activeScenarioId_.clear();
        setStatus(QString::fromUtf8("ROM-каталог перевірено; сценарії доступні"));
    }
    // C2b validation and copy are pure preflight; only Qt owns the executing CPU.
    bool operatorCall(const QStringList& args,QJsonObject& result,QString& error){
        const QString tool=repoFile(QStringLiteral("tools/historical/qt_h118_operator_v1.py"));
        if(!QFileInfo(tool).isFile()){error=QStringLiteral("H118 operator bridge missing");return false;}
        QProcess process;
        process.setWorkingDirectory(root_);
        process.start(QStringLiteral("python"),QStringList{QStringLiteral("-B"),tool,
                          QStringLiteral("--repo"),root_}+args);
        if(!process.waitForStarted(4000)){
            error=QStringLiteral("Cannot start Python: ")+process.errorString();return false;
        }
        if(!process.waitForFinished(30000)){
            process.kill();process.waitForFinished(1000);
            error=QStringLiteral("H118 operator preflight timeout");return false;
        }
        const auto output=process.readAllStandardOutput();
        const auto diag=process.readAllStandardError();
        if(process.exitStatus()!=QProcess::NormalExit||process.exitCode()!=0||output.size()>131072){
            error=QString::fromUtf8(diag.left(450));return false;
        }
        QJsonParseError pe;
        const auto doc=QJsonDocument::fromJson(output,&pe);
        if(pe.error!=QJsonParseError::NoError||!doc.isObject()){
            error=QStringLiteral("Invalid H118 operator JSON");return false;
        }
        result=doc.object();
        if(!result.value(QStringLiteral("status")).toString().startsWith(QStringLiteral("PASS_H118_OPERATOR_"))){
            error=QStringLiteral("H118 operator preflight HOLD");return false;
        }
        return true;
    }
    void populateOperators(){
        if(operatorActive_)return;
        QJsonObject report;QString error;
        if(!operatorCall({QStringLiteral("list")},report,error)){
            setStatus(QStringLiteral("C2b catalog HOLD: ")+error);return;
        }
        const QString previous=operatorSelect_->currentData().toString();
        QSignalBlocker block(operatorSelect_);
        operatorSelect_->clear();
        operatorSelect_->addItem(QString::fromUtf8("— обрати C2b сценарій —"),QString());
        for(const auto& value:report.value(QStringLiteral("items")).toArray()){
            const auto item=value.toObject();
            const QString id=item.value(QStringLiteral("id")).toString();
            operatorSelect_->addItem(id,id);
            operatorSelect_->setItemData(operatorSelect_->count()-1,
                item.value(QStringLiteral("origin")).toString()+QStringLiteral(" · ")+
                item.value(QStringLiteral("description")).toString(),Qt::ToolTipRole);
        }
        const int index=operatorSelect_->findData(previous);
        operatorSelect_->setCurrentIndex(index>=0?index:0);
        updateButtons();
    }
    static QMap<QString,QString> responseMap(const QStringList& parts){
        QMap<QString,QString> data;
        for(int i=2;i<parts.size();++i){
            const int eq=parts[i].indexOf('=');
            if(eq<=0)continue;
            const QString key=parts[i].left(eq);
            if(data.contains(key))return {};
            data.insert(key,parts[i].mid(eq+1));
        }
        return data;
    }
    bool stateMatches(const QMap<QString,QString>& data,const QJsonObject& expected) const {
        for(auto it=expected.begin();it!=expected.end();++it){
            const QString value=it.value().isDouble()
                   ?QString::number(it.value().toInt()):it.value().toString();
            if(data.value(it.key())!=value)return false;
        }
        return true;
    }
    QString operatorCommand(const QJsonObject& a) const {
        const QString op=a.value(QStringLiteral("op")).toString();
        if(op==QStringLiteral("set_nk"))return QStringLiteral("SETNK\t")+a.value(QStringLiteral("address")).toString()+QStringLiteral("\t")+a.value(QStringLiteral("word")).toString();
        if(op==QStringLiteral("clear_nk"))return QStringLiteral("CLEARNK\t")+a.value(QStringLiteral("address")).toString();
        if(op==QStringLiteral("step"))return QStringLiteral("STEP\t")+QString::number(a.value(QStringLiteral("count")).toInt());
        if(op==QStringLiteral("dump"))return QStringLiteral("DUMP\t")+a.value(QStringLiteral("address")).toString()+QStringLiteral("\t")+QString::number(a.value(QStringLiteral("count")).toInt());
        if(op==QStringLiteral("state"))return QStringLiteral("STATE");
        if(op==QStringLiteral("save"))return QStringLiteral("SAVE");
        if(op==QStringLiteral("restore"))return QStringLiteral("RESTORE");
        return {};
    }
    void operatorHold(const QString& reason){
        operatorActive_=false;operatorWaitingLoad_=false;running_=false;
        requests_.clear();
        traceArea_->appendPlainText(QStringLiteral("H118 C2b HOLD: ")+reason);
        setStatus(QStringLiteral("C2b HOLD: ")+reason);
        updateButtons();
    }
    void queueNextOperator(){
        if(!operatorActive_||operatorWaitingLoad_)return;
        if(operatorIndex_==operatorActions_.size()){
            operatorActive_=false;
            traceArea_->appendPlainText(QStringLiteral("PASS_H118_C2B_GUI_PERSISTENT_HOST_NOT_HARDWARE"));
            setStatus(QString::fromUtf8("C2b PASS — усі дії та oracle перевірені на CPU (не апаратний доказ)"));
            updateButtons();
            return;
        }
        const QJsonObject a=operatorActions_.at(operatorIndex_).toObject();
        const QString line=operatorCommand(a);
        if(line.isEmpty()){operatorHold(QStringLiteral("UNKNOWN_ACTION"));return;}
        requests_.enqueue({line.section('\t',0,0),line});
    }
    bool checkOperatorResponse(const QStringList& fields,QString& reason){
        if(operatorIndex_>=operatorActions_.size()){
            reason=QStringLiteral("ACTION_OVERFLOW");return false;
        }
        const auto a=operatorActions_.at(operatorIndex_).toObject();
        const QString op=a.value(QStringLiteral("op")).toString();
        const QMap<QString,QString> data=responseMap(fields);
        if(data.isEmpty()){reason=QStringLiteral("MISSING_RESPONSE_FIELDS");return false;}
        bool correct=false;
        if(op==QStringLiteral("set_nk"))
            correct=data.value(QStringLiteral("ADDR"))==a.value(QStringLiteral("address")).toString() &&
                    data.value(QStringLiteral("WORD"))==a.value(QStringLiteral("word")).toString();
        else if(op==QStringLiteral("clear_nk"))
            correct=data.value(QStringLiteral("ADDR"))==a.value(QStringLiteral("address")).toString();
        else if(op==QStringLiteral("state"))
            correct=stateMatches(data,a.value(QStringLiteral("expect")).toObject());
        else if(op==QStringLiteral("step")){
            const auto expected=a.value(QStringLiteral("expect")).toObject();
            QStringList pcs;
            for(const auto& v:expected.value(QStringLiteral("path")).toArray())pcs<<v.toString();
            correct=data.value(QStringLiteral("EXECUTED"))==QString::number(expected.value(QStringLiteral("executed")).toInt()) &&
                    data.value(QStringLiteral("PATH"))==pcs.join(',') &&
                    stateMatches(data,expected.value(QStringLiteral("state")).toObject());
        }else if(op==QStringLiteral("dump")){
            QStringList values;
            for(const auto& v:a.value(QStringLiteral("expect")).toArray())values<<v.toString();
            correct=data.value(QStringLiteral("START"))==a.value(QStringLiteral("address")).toString() &&
                    data.value(QStringLiteral("COUNT"))==QString::number(a.value(QStringLiteral("count")).toInt()) &&
                    data.value(QStringLiteral("DATA"))==values.join(',');
        }else if(op==QStringLiteral("save")||op==QStringLiteral("restore"))
            correct=data.contains(QStringLiteral("C")) && data.contains(QStringLiteral("STEPS"));
        if(!correct){reason=QStringLiteral("ACTION_%1_ORACLE_MISMATCH_%2").arg(operatorIndex_).arg(op);return false;}
        traceArea_->appendPlainText(QStringLiteral("C2b %1 %2: %3").arg(operatorIndex_+1).arg(op).arg(fields.mid(2).join(' ')).left(550));
        if(op==QStringLiteral("step")||op==QStringLiteral("restore")||op==QStringLiteral("state"))applyState(fields.mid(2));
        return true;
    }
    void startOperatorReplay(){
        if(operatorActive_||running_||busy_||!ready_||!requests_.isEmpty())return;
        const QString id=operatorSelect_->currentData().toString();
        if(id.isEmpty())return;
        auto temporary=std::make_unique<QTemporaryDir>(repoFile(QStringLiteral("tempkyiv/qt_h118_op_XXXXXX")));
        if(!temporary->isValid()){
            alert(this,QStringLiteral("H118: cannot create tempkyiv directory"));return;
        }
        const QString output=QDir(temporary->path()).absoluteFilePath(QStringLiteral("prepared"));
        QJsonObject report;QString error;
        if(!operatorCall({QStringLiteral("prepare"),id,QStringLiteral("--out"),output},report,error)){
            alert(this,QStringLiteral("C2b preflight HOLD: ")+error);return;
        }
        if(report.value(QStringLiteral("id")).toString()!=id || !report.value(QStringLiteral("actions")).isArray()){
            alert(this,QStringLiteral("C2b response identity mismatch"));return;
        }
        const QString romFile=report.value(QStringLiteral("rom_path")).toString();
        const QString romSha=report.value(QStringLiteral("rom_sha256")).toString();
        const QString program=report.value(QStringLiteral("program_path")).toString();
        const QString programSha=report.value(QStringLiteral("program_sha256")).toString();
        auto matches=[](const QString& path,const QString& expected){
            QFile file(path);
            if(!file.open(QIODevice::ReadOnly))return false;
            return expected.size()==64 && QCryptographicHash::hash(file.readAll(),QCryptographicHash::Sha256).toHex()==expected.toLatin1();
        };
        if(!matches(romFile,romSha)||!matches(program,programSha)){
            alert(this,QStringLiteral("C2b pinned image SHA mismatch"));return;
        }
        const QString entry=report.value(QStringLiteral("entry")).toString();
        quint64 start=0;
        if(!parseOct(entry,4,01777,start)||start==0){alert(this,QStringLiteral("C2b invalid entry"));return;}
        if(!restartForRom({rom_,QStringLiteral("--rom-set-image"),romFile,
                           QStringLiteral("--rom-set-sha256"),romSha},
                           report.value(QStringLiteral("rom_set")).toString()))return;
        // Retain validated input and the action plan until replay completes.
        temporary->setAutoRemove(false);  // Private reproducibility evidence is retained.
        preparedRom_=std::move(temporary);
        operatorActions_=report.value(QStringLiteral("actions")).toArray();
        operatorIndex_=0;operatorActive_=true;operatorWaitingLoad_=true;operatorId_=id;
        loadedOracle_={};pendingOracle_={};oracleAuditing_=false;oracleFinished_=true;
        loadedRunMode_=QStringLiteral("image");fpDone_=false;
        requests_.enqueue({QStringLiteral("LOAD"),QStringLiteral("LOAD\t")+program+QStringLiteral("\t")+entry});
        updateButtons();
        setStatus(QStringLiteral("C2b replay: ")+id);
    }
    void invalidateOracle(){
        if(!loadedOracle_.isEmpty()&&!oracleFinished_){
            oracleEligible_=false;
            traceArea_->appendPlainText(QStringLiteral("C2a oracle skipped: manual NK/checkpoint change"));
        }
    }
    void oracleHold(const QString& reason){
        running_=false;oracleAuditing_=false;oracleFinished_=true;
        traceArea_->appendPlainText(QStringLiteral("H118 C2a HOLD: ")+reason);
        setStatus(QStringLiteral("C2a HOLD: ")+reason);updateButtons();
    }
    void nextOracleWatch(){
        if(!oracleAuditing_)return;
        if(oracleWatchIndex_>=oracleWatchAddresses_.size()){
            oracleAuditing_=false;oracleFinished_=true;
            traceArea_->appendPlainText(QStringLiteral("PASS_H118_C2A_GUI_NATIVE_ORACLE_NOT_HARDWARE"));
            setStatus(QString::fromUtf8("C2a PASS — машинні слова й лічильники збігаються (не історичний oracle)"));
            updateButtons();return;
        }
        const QString addr=oracleWatchAddresses_.at(oracleWatchIndex_);
        requests_.enqueue({QStringLiteral("DUMP"),QStringLiteral("DUMP\t")+addr+QStringLiteral("\t1")});
    }
    void startOracleAudit(){
        if(loadedOracle_.isEmpty()||oracleFinished_||oracleAuditing_)return;
        if(!oracleEligible_){
            oracleHold(QStringLiteral("MANUAL_STATE_MODIFICATION"));return;
        }
        const QString expectedStatus=loadedOracle_.value(QStringLiteral("status")).toString();
        const QString status=fpDone_?QStringLiteral("END_POINTER"):(t_?QStringLiteral("CPU_STOP"):QStringLiteral("LIMIT"));
        if(status!=expectedStatus){oracleHold(QStringLiteral("STATUS_EXPECTED_%1_ACTUAL_%2").arg(expectedStatus,status));return;}
        if(actualSteps_!=quint64(loadedOracle_.value(QStringLiteral("steps")).toInt())){
            oracleHold(QStringLiteral("STEP_COUNT_MISMATCH"));return;
        }
        if(expectedStatus==QStringLiteral("END_POINTER") &&
            fpDispatches_!=quint64(loadedOracle_.value(QStringLiteral("dispatches")).toInt())){
            oracleHold(QStringLiteral("FP_DISPATCH_COUNT_MISMATCH"));return;
        }
        const auto watched=loadedOracle_.value(QStringLiteral("watches")).toObject();
        oracleWatchAddresses_=watched.keys();oracleWatchIndex_=0;
        if(oracleWatchAddresses_.isEmpty()){oracleHold(QStringLiteral("NO_WATCHES"));return;}
        oracleAuditing_=true;
        traceArea_->appendPlainText(QStringLiteral("C2a: terminal status/steps/dispatches matched; checking RAM/ROM"));
        nextOracleWatch();
    }
    // Destroying a session is deliberate only when the selected ROM set changes.
    bool restartForRom(const QStringList& args,const QString& set){
        backend_.disconnect(this);
        if(backend_.state()==QProcess::Running){
            backend_.write("QUIT\n");backend_.closeWriteChannel();
            if(!backend_.waitForFinished(1300)){
                backend_.kill();backend_.waitForFinished(1300);
            }
        }
        if(backend_.state()!=QProcess::NotRunning){
            fatal(QString::fromUtf8("Не вдалося зупинити стару CPU-сесію"));return false;
        }
        // Old QUIT acknowledgement belongs to the discarded process, not to PING.
        backend_.readAllStandardOutput();
        backend_.readAllStandardError();
        ready_=false;loaded_=false;faulted_=false;running_=false;busy_=false;t_=false;fpDone_=false;
        updateFpDispatches();
        readBuffer_.clear();requests_.clear();inFlight_={};
        activeBackendSet_=set;
        startBackend(args);
        return true;
    }
    void loadImage() {
        running_=false;batchCount_=0;
        quint64 start=0;
        if(!parseOct(startEdit_->text(),4,03777,start)||start==0) {alert(this,QString::fromUtf8("Старт має містити 4 вісімкові цифри та допустиму адресу."));return;}
        if(image_.isEmpty()||!QFileInfo::exists(image_)) {alert(this,QString::fromUtf8("Файл образу не знайдено."));return;}
        if(image_.contains('\t')||image_.contains('\r')||image_.contains('\n')) {alert(this,QString::fromUtf8("Неприпустимі символи в шляху."));return;}
        QString program=QFileInfo(image_).absoluteFilePath();
        const QString selected=romSets_->currentData().toString();
        const bool fp=selectedRunMode_==QStringLiteral("fp-image");
        if(fp && selected.isEmpty()) {
            alert(this,QString::fromUtf8("Для запуску через МП необхідний FP-ROM"));return;
        }
        quint64 end=0;
        if(fp && (!parseOct(selectedEndPointer_,4,01777,end) || end==0)) {
            alert(this,QString::fromUtf8("Для МП потрібний коректний end-pointer"));return;
        }
        const QString dual=repoFile(QStringLiteral("examples/dual_euler_reconstructed/EULER_DUAL_MODE.k41"));
        if(QFileInfo(program).absoluteFilePath()==QFileInfo(dual).absoluteFilePath()) {
            QFile f(dual);
            if(!f.open(QIODevice::ReadOnly) ||
               QCryptographicHash::hash(f.readAll(),QCryptographicHash::Sha256).toHex()!=
                 QByteArrayLiteral("6312ad73e0ae6268016777126bf1f92c214819a94e00dabf5785bb51b0de7a9e")) {
                alert(this,QString::fromUtf8("Експериментальний образ Dual Euler: SHA-256 не збігається"));return;
            }
        }
        QJsonObject nextOracle;  // Only published after CPU LOAD succeeds.
        const QString loadKind=fp?QStringLiteral("LOADFP"):QStringLiteral("LOAD");
        auto loadLine=[&](){return loadKind+QStringLiteral("\t")+program+
             QStringLiteral("\t")+octal(start,4)+
             (fp?QStringLiteral("\t")+selectedEndPointer_:QString());};
        if(!selected.isEmpty()){
            auto temporary=std::make_unique<QTemporaryDir>(
                repoFile(QStringLiteral("tempkyiv/qt_h1_rom_XXXXXX")));
            if(!temporary->isValid()){
                alert(this,QString::fromUtf8("Не вдалося створити приватний каталог ROM"));return;
            }
            QJsonObject manifest;QString error;
            QStringList args{QStringLiteral("prepare"),selected,QStringLiteral("--out"),
                             QDir(temporary->path()).absoluteFilePath(QStringLiteral("set"))};
            if(!activeScenarioId_.isEmpty()){
                args<<QStringLiteral("--scenario")<<activeScenarioId_;
            }
            if(!catalogCall(args,manifest,error)){
                alert(this,QString::fromUtf8("ROM-комплект не пройшов перевірку: ")+error);
                return; // Keep the currently running CPU unchanged.
            }
            if(manifest.value(QStringLiteral("set")).toString()!=selected){
                alert(this,QString::fromUtf8("Помилка ідентичності ROM-комплекту"));return;
            }
            if(!activeScenarioId_.isEmpty()){
                if(manifest.value(QStringLiteral("scenario_id")).toString()!=activeScenarioId_){
                    alert(this,QString::fromUtf8("Помилка ідентичності сценарію"));return;
                }
                program=manifest.value(QStringLiteral("program_path")).toString();
                nextOracle=manifest.value(QStringLiteral("oracle")).toObject();
                if(nextOracle.value(QStringLiteral("id")).toString()!=activeScenarioId_ ||
                   nextOracle.value(QStringLiteral("mode")).toString()!=selectedRunMode_){
                    alert(this,QStringLiteral("C2a oracle identity mismatch"));return;
                }
                const QString entry=manifest.value(QStringLiteral("entry")).toString();
                if(entry!=octal(start,4)||!QFileInfo(program).isFile()){
                    alert(this,QString::fromUtf8("Старт або програма сценарію змінилися"));return;
                }
                // Recheck the pinned staged RAM bytes immediately before LOAD,
                // not just the Python preflight's original/tracked source.
                QFile pinnedProgram(program);
                const QString programSha=manifest.value(QStringLiteral("program_sha256")).toString();
                if(!pinnedProgram.open(QIODevice::ReadOnly)||programSha.size()!=64||
                   QCryptographicHash::hash(pinnedProgram.readAll(),QCryptographicHash::Sha256).toHex()!=programSha.toLatin1()){
                    alert(this,QStringLiteral("C2a staged RAM SHA mismatch"));return;
                }
            }
            const QString romImage=manifest.value(QStringLiteral("rom_path")).toString();
            const QString sha=manifest.value(QStringLiteral("sha256")).toString();
            if(!QFileInfo(romImage).isFile()||sha.size()!=64){
                alert(this,QString::fromUtf8("Неповний підготовлений ROM-образ"));return;
            }
            const QByteArray digest=QCryptographicHash::hash(
                [&](){QFile f(romImage);if(!f.open(QIODevice::ReadOnly))return QByteArray();
                return f.readAll();}(),QCryptographicHash::Sha256).toHex();
            if(QString::fromLatin1(digest)!=sha){
                alert(this,QString::fromUtf8("SHA-256 ROM-образу не збігається"));return;
            }
            // Keep the staged files alive while the persistent backend runs.
            if(!restartForRom({rom_,QStringLiteral("--rom-set-image"),romImage,
                               QStringLiteral("--rom-set-sha256"),sha},selected))return;
            preparedRom_=std::move(temporary);
            pendingOracle_=nextOracle;
            loadedRunMode_=fp?QStringLiteral("fp-image"):QStringLiteral("image");fpDone_=false;
            requests_.enqueue({loadKind,loadLine()});
        }else{
            if(!activeBackendSet_.isEmpty()){
                if(!restartForRom({rom_},QString()))return;
                preparedRom_.reset();
                pendingOracle_={};
                loadedRunMode_=fp?QStringLiteral("fp-image"):QStringLiteral("image");fpDone_=false;
                requests_.enqueue({loadKind,loadLine()});
            }else{
                requests_.clear();
                pendingOracle_={};
                loadedRunMode_=fp?QStringLiteral("fp-image"):QStringLiteral("image");fpDone_=false;
                enqueue({loadKind,loadLine()});
            }
        }
        updateButtons();
    }
    void refreshMemory(){
        if(operatorActive_)return;
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
        actualSteps_=map.value(QStringLiteral("STEPS")).toULongLong();
        fpDispatches_=map.value(QStringLiteral("DISPATCHES")).toULongLong();
        parseOct(map.value("C"),4,03777,c_);parseOct(map.value("K"),14,(quint64(1)<<41)-1,command_);
        parseOct(map.value("A"),4,03777,a_);parseOct(map.value("P"),4,03777,p_);parseOct(map.value("LOOP"),4,03777,loop_);
        t_=map.value("T")=="1";
        fpDone_=(loadedRunMode_==QStringLiteral("fp-image") &&
                 map.value(QStringLiteral("END_POINTER"))==QStringLiteral("1"));
        updateFpDispatches();
        lamps_->setState(command_,c_,a_,p_,loop_,t_);
        if(t_ || fpDone_)running_=false;
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
            if(operatorActive_){
                busy_=false;faulted_=true;
                operatorHold(QStringLiteral("BACKEND_ERROR: ")+fields.mid(1).join(' '));return;
            }
            if(oracleAuditing_){busy_=false;oracleHold(QStringLiteral("BACKEND_DUMP_ERROR"));return;}
            busy_=false;running_=false;
            setStatus(QString::fromUtf8("Помилка CPU: ")+fields.mid(1).join(' '));
            updateButtons();pump();return;
        }
        if(fields[0]!="OK"||fields.size()<2||fields[1]!=inFlight_.kind) {
            fatal(QString::fromUtf8("Неочікувана відповідь backend: ")+line);return;
        }
        const QString kind=inFlight_.kind;
        busy_=false;
        if(operatorActive_&&!operatorWaitingLoad_ && kind!="LOAD" && kind!="LOADFP"){
            QString reason;
            if(!checkOperatorResponse(fields,reason)){operatorHold(reason);return;}
            ++operatorIndex_;queueNextOperator();updateButtons();pump();return;
        }
        if(kind=="LOAD"||kind=="LOADFP") {
            loaded_=true;faulted_=false;traceArea_->clear();
            traceArea_->appendPlainText(operatorActive_
                ?QStringLiteral("H118 C2b live replay: ")+operatorId_
                :QString::fromUtf8("Завантажено: ")+image_);
            loadedOracle_=pendingOracle_;pendingOracle_={};
            oracleEligible_=true;oracleFinished_=loadedOracle_.isEmpty();oracleAuditing_=false;
            imageInfo_->setText(fields.size()>2?fields[2]:QString::fromUtf8("Завантажено"));
            applyState(fields.mid(2));
            setStatus(QString::fromUtf8("Образ завантажено"));
            if(operatorActive_){
                operatorWaitingLoad_=false;queueNextOperator();
            }else requests_.enqueue({"DUMP",QStringLiteral("DUMP\t%1\t32").arg(octal(memStart_,4))});
        } else if(kind=="STEP") {
            ++batchCount_;
            QString path;
            for(const auto& field:fields)if(field.startsWith("PATH="))path=field.mid(5);
            if(!path.isEmpty()&&path!="-") {
                const QStringList pcs=path.split(',');
                for(const auto& pc:pcs)traceArea_->appendPlainText(pc);
            }
            applyState(fields.mid(2));
            if(fpDone_)setStatus(QString::fromUtf8("МП завершила програму на межі диспетчера (не STOP)"));
            else if(t_)setStatus(QString::fromUtf8("CPU зупинено (STOP або аварійний останов)"));
            if(!running_||t_||fpDone_||batchCount_%12==0)
                requests_.enqueue({"DUMP",QStringLiteral("DUMP\t%1\t32").arg(octal(memStart_,4))});
            if((t_||fpDone_) && !loadedOracle_.isEmpty() && !oracleFinished_)startOracleAudit();
        } else if(kind=="DUMP") {
            QString data, start;
            for(const auto& field:fields){if(field.startsWith("DATA="))data=field.mid(5);if(field.startsWith("START="))start=field.mid(6);}
            bool ok=false;const int base=start.toInt(&ok,8);
            const QStringList words=data.split(',');
            if(oracleAuditing_ && inFlight_.line.endsWith(QStringLiteral("\t1"))){
                const QString expectedAddress=oracleWatchAddresses_.at(oracleWatchIndex_);
                const QString expectedWord=loadedOracle_.value(QStringLiteral("watches")).toObject().value(expectedAddress).toString();
                if(!ok||start!=expectedAddress||words.size()!=1||words.at(0)!=expectedWord){
                    oracleHold(QStringLiteral("WATCH_MISMATCH_%1").arg(expectedAddress));return;
                }
                traceArea_->appendPlainText(QStringLiteral("oracle [%1] = %2").arg(expectedAddress,words.at(0)));
                ++oracleWatchIndex_;nextOracleWatch();updateButtons();pump();return;
            }
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
    void startBackend(const QStringList& customArgs={}) {
        const QString exe=QDir(QCoreApplication::applicationDirPath()).absoluteFilePath(
#ifdef Q_OS_WIN
            QStringLiteral("kyiv_gui_backend.exe")
#else
            QStringLiteral("kyiv_gui_backend")
#endif
        );
        if(!QFileInfo::exists(exe)){fatal(QString::fromUtf8("Не знайдено backend: ")+exe);return;}
        backend_.setProgram(exe);
        backend_.setArguments(customArgs.isEmpty()?QStringList{rom_}:customArgs);
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
        makeUI();populateCatalog();populateOperators();startBackend();
    }
    ~MainWindow() override {
        runTimer_.stop();
        // waitForFinished() may deliver OK QUIT; no more UI callbacks on teardown.
        backend_.disconnect(this);
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
