// Generated file: Vcheck.cpp
// Verilated -*- C++ -*-
// DESCRIPTION: Verilator output: Model implementation (design independent parts)

#include "Vcheck__pch.h"

//============================================================
// Constructors

Vcheck::Vcheck(VerilatedContext* _vcontextp__, const char* _vcname__)
    : VerilatedModel{*_vcontextp__}
    , vlSymsp{new Vcheck__Syms(contextp(), _vcname__, this)}
    , clk{vlSymsp->TOP.clk}
    , bad{vlSymsp->TOP.bad}
    , rootp{&(vlSymsp->TOP)}
{
    // Register model with the context
    contextp()->addModel(this);
}

Vcheck::Vcheck(const char* _vcname__)
    : Vcheck(Verilated::threadContextp(), _vcname__)
{
}

//============================================================
// Destructor

Vcheck::~Vcheck() {
    delete vlSymsp;
}

//============================================================
// Evaluation function

#ifdef VL_DEBUG
void Vcheck___024root___eval_debug_assertions(Vcheck___024root* vlSelf);
#endif  // VL_DEBUG
void Vcheck___024root___eval_static(Vcheck___024root* vlSelf);
void Vcheck___024root___eval_initial(Vcheck___024root* vlSelf);
void Vcheck___024root___eval_settle(Vcheck___024root* vlSelf);
void Vcheck___024root___eval(Vcheck___024root* vlSelf);

void Vcheck::eval_step() {
    VL_DEBUG_IF(VL_DBG_MSGF("+++++TOP Evaluate Vcheck::eval_step\n"); );
#ifdef VL_DEBUG
    // Debug assertions
    Vcheck___024root___eval_debug_assertions(&(vlSymsp->TOP));
#endif  // VL_DEBUG
    vlSymsp->__Vm_deleter.deleteAll();
    if (VL_UNLIKELY(!vlSymsp->__Vm_didInit)) {
        vlSymsp->__Vm_didInit = true;
        VL_DEBUG_IF(VL_DBG_MSGF("+ Initial\n"););
        Vcheck___024root___eval_static(&(vlSymsp->TOP));
        Vcheck___024root___eval_initial(&(vlSymsp->TOP));
        Vcheck___024root___eval_settle(&(vlSymsp->TOP));
    }
    VL_DEBUG_IF(VL_DBG_MSGF("+ Eval\n"););
    Vcheck___024root___eval(&(vlSymsp->TOP));
    // Evaluate cleanup
    Verilated::endOfEval(vlSymsp->__Vm_evalMsgQp);
}

//============================================================
// Events and timing
bool Vcheck::eventsPending() { return false; }

uint64_t Vcheck::nextTimeSlot() {
    VL_FATAL_MT(__FILE__, __LINE__, "", "%Error: No delays in the design");
    return 0;
}

//============================================================
// Utilities

const char* Vcheck::name() const {
    return vlSymsp->name();
}

//============================================================
// Invoke final blocks

void Vcheck___024root___eval_final(Vcheck___024root* vlSelf);

VL_ATTR_COLD void Vcheck::final() {
    Vcheck___024root___eval_final(&(vlSymsp->TOP));
}

//============================================================
// Implementations of abstract methods from VerilatedModel

const char* Vcheck::hierName() const { return vlSymsp->name(); }
const char* Vcheck::modelName() const { return "Vcheck"; }
unsigned Vcheck::threads() const { return 1; }
void Vcheck::prepareClone() const { contextp()->prepareClone(); }
void Vcheck::atClone() const {
    contextp()->threadPoolpOnClone();
}

//============================================================
// Trace configuration

VL_ATTR_COLD void Vcheck::trace(VerilatedVcdC* tfp, int levels, int options) {
    vl_fatal(__FILE__, __LINE__, __FILE__,"'Vcheck::trace()' called on model that was Verilated without --trace option");
}

// Generated file: Vcheck__Syms.cpp
// Verilated -*- C++ -*-
// DESCRIPTION: Verilator output: Symbol table implementation internals

#include "Vcheck__pch.h"
#include "Vcheck.h"
#include "Vcheck___024root.h"

// FUNCTIONS
Vcheck__Syms::~Vcheck__Syms()
{
}

Vcheck__Syms::Vcheck__Syms(VerilatedContext* contextp, const char* namep, Vcheck* modelp)
    : VerilatedSyms{contextp}
    // Setup internal state of the Syms class
    , __Vm_modelp{modelp}
    // Setup module instances
    , TOP{this, namep}
{
        // Check resources
        Verilated::stackCheck(11);
    // Configure time unit / time precision
    _vm_contextp__->timeunit(-12);
    _vm_contextp__->timeprecision(-12);
    // Setup each module's pointers to their submodules
    // Setup each module's pointer back to symbol table (for public functions)
    TOP.__Vconfigure(true);
    // Setup scopes
    __Vscope_check.configure(this, name(), "check", "check", -12, VerilatedScope::SCOPE_OTHER);
}

// Generated file: Vcheck___024root__DepSet_h0ef4225e__0.cpp
// Verilated -*- C++ -*-
// DESCRIPTION: Verilator output: Design implementation internals
// See Vcheck.h for the primary calling header

#include "Vcheck__pch.h"
#include "Vcheck__Syms.h"
#include "Vcheck___024root.h"

#ifdef VL_DEBUG
VL_ATTR_COLD void Vcheck___024root___dump_triggers__act(Vcheck___024root* vlSelf);
#endif  // VL_DEBUG

void Vcheck___024root___eval_triggers__act(Vcheck___024root* vlSelf) {
    (void)vlSelf;  // Prevent unused variable warning
    Vcheck__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vcheck___024root___eval_triggers__act\n"); );
    // Body
    vlSelf->__VactTriggered.set(0U, ((IData)(vlSelf->clk) 
                                     & (~ (IData)(vlSelf->__Vtrigprevexpr___TOP__clk__0))));
    vlSelf->__Vtrigprevexpr___TOP__clk__0 = vlSelf->clk;
#ifdef VL_DEBUG
    if (VL_UNLIKELY(vlSymsp->_vm_contextp__->debug())) {
        Vcheck___024root___dump_triggers__act(vlSelf);
    }
#endif
}

VL_INLINE_OPT void Vcheck___024root___nba_sequent__TOP__0(Vcheck___024root* vlSelf) {
    (void)vlSelf;  // Prevent unused variable warning
    Vcheck__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vcheck___024root___nba_sequent__TOP__0\n"); );
    // Body
    if (VL_UNLIKELY(vlSelf->bad)) {
        VL_WRITEF_NX("[%0t] %%Error: check.sv:3: Assertion failed in %Ncheck: PROC_ERROR\n",0,
                     64,VL_TIME_UNITED_Q(1),-12,vlSymsp->name());
        VL_STOP_MT("${PROBE_ROOT}/check.sv", 3, "");
    }
    if (VL_UNLIKELY(vlSelf->bad)) {
        VL_WRITEF_NX("[%0t] %%Fatal: check.sv:4: Assertion failed in %Ncheck: PROC_FATAL\n",0,
                     64,VL_TIME_UNITED_Q(1),-12,vlSymsp->name());
        VL_STOP_MT("${PROBE_ROOT}/check.sv", 4, "");
    }
}

// Generated file: Vcheck___024root__DepSet_h23112b51__0.cpp
// Verilated -*- C++ -*-
// DESCRIPTION: Verilator output: Design implementation internals
// See Vcheck.h for the primary calling header

#include "Vcheck__pch.h"
#include "Vcheck___024root.h"

void Vcheck___024root___eval_act(Vcheck___024root* vlSelf) {
    (void)vlSelf;  // Prevent unused variable warning
    Vcheck__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vcheck___024root___eval_act\n"); );
}

void Vcheck___024root___nba_sequent__TOP__0(Vcheck___024root* vlSelf);

void Vcheck___024root___eval_nba(Vcheck___024root* vlSelf) {
    (void)vlSelf;  // Prevent unused variable warning
    Vcheck__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vcheck___024root___eval_nba\n"); );
    // Body
    if ((1ULL & vlSelf->__VnbaTriggered.word(0U))) {
        Vcheck___024root___nba_sequent__TOP__0(vlSelf);
    }
}

void Vcheck___024root___eval_triggers__act(Vcheck___024root* vlSelf);

bool Vcheck___024root___eval_phase__act(Vcheck___024root* vlSelf) {
    (void)vlSelf;  // Prevent unused variable warning
    Vcheck__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vcheck___024root___eval_phase__act\n"); );
    // Init
    VlTriggerVec<1> __VpreTriggered;
    CData/*0:0*/ __VactExecute;
    // Body
    Vcheck___024root___eval_triggers__act(vlSelf);
    __VactExecute = vlSelf->__VactTriggered.any();
    if (__VactExecute) {
        __VpreTriggered.andNot(vlSelf->__VactTriggered, vlSelf->__VnbaTriggered);
        vlSelf->__VnbaTriggered.thisOr(vlSelf->__VactTriggered);
        Vcheck___024root___eval_act(vlSelf);
    }
    return (__VactExecute);
}

bool Vcheck___024root___eval_phase__nba(Vcheck___024root* vlSelf) {
    (void)vlSelf;  // Prevent unused variable warning
    Vcheck__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vcheck___024root___eval_phase__nba\n"); );
    // Init
    CData/*0:0*/ __VnbaExecute;
    // Body
    __VnbaExecute = vlSelf->__VnbaTriggered.any();
    if (__VnbaExecute) {
        Vcheck___024root___eval_nba(vlSelf);
        vlSelf->__VnbaTriggered.clear();
    }
    return (__VnbaExecute);
}

#ifdef VL_DEBUG
VL_ATTR_COLD void Vcheck___024root___dump_triggers__nba(Vcheck___024root* vlSelf);
#endif  // VL_DEBUG
#ifdef VL_DEBUG
VL_ATTR_COLD void Vcheck___024root___dump_triggers__act(Vcheck___024root* vlSelf);
#endif  // VL_DEBUG

void Vcheck___024root___eval(Vcheck___024root* vlSelf) {
    (void)vlSelf;  // Prevent unused variable warning
    Vcheck__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vcheck___024root___eval\n"); );
    // Init
    IData/*31:0*/ __VnbaIterCount;
    CData/*0:0*/ __VnbaContinue;
    // Body
    __VnbaIterCount = 0U;
    __VnbaContinue = 1U;
    while (__VnbaContinue) {
        if (VL_UNLIKELY((0x64U < __VnbaIterCount))) {
#ifdef VL_DEBUG
            Vcheck___024root___dump_triggers__nba(vlSelf);
#endif
            VL_FATAL_MT("${PROBE_ROOT}/check.sv", 1, "", "NBA region did not converge.");
        }
        __VnbaIterCount = ((IData)(1U) + __VnbaIterCount);
        __VnbaContinue = 0U;
        vlSelf->__VactIterCount = 0U;
        vlSelf->__VactContinue = 1U;
        while (vlSelf->__VactContinue) {
            if (VL_UNLIKELY((0x64U < vlSelf->__VactIterCount))) {
#ifdef VL_DEBUG
                Vcheck___024root___dump_triggers__act(vlSelf);
#endif
                VL_FATAL_MT("${PROBE_ROOT}/check.sv", 1, "", "Active region did not converge.");
            }
            vlSelf->__VactIterCount = ((IData)(1U) 
                                       + vlSelf->__VactIterCount);
            vlSelf->__VactContinue = 0U;
            if (Vcheck___024root___eval_phase__act(vlSelf)) {
                vlSelf->__VactContinue = 1U;
            }
        }
        if (Vcheck___024root___eval_phase__nba(vlSelf)) {
            __VnbaContinue = 1U;
        }
    }
}

#ifdef VL_DEBUG
void Vcheck___024root___eval_debug_assertions(Vcheck___024root* vlSelf) {
    (void)vlSelf;  // Prevent unused variable warning
    Vcheck__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vcheck___024root___eval_debug_assertions\n"); );
    // Body
    if (VL_UNLIKELY((vlSelf->clk & 0xfeU))) {
        Verilated::overWidthError("clk");}
    if (VL_UNLIKELY((vlSelf->bad & 0xfeU))) {
        Verilated::overWidthError("bad");}
}
#endif  // VL_DEBUG

// Generated file: Vcheck___024root__DepSet_h23112b51__0__Slow.cpp
// Verilated -*- C++ -*-
// DESCRIPTION: Verilator output: Design implementation internals
// See Vcheck.h for the primary calling header

#include "Vcheck__pch.h"
#include "Vcheck___024root.h"

VL_ATTR_COLD void Vcheck___024root___eval_static(Vcheck___024root* vlSelf) {
    (void)vlSelf;  // Prevent unused variable warning
    Vcheck__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vcheck___024root___eval_static\n"); );
}

VL_ATTR_COLD void Vcheck___024root___eval_initial(Vcheck___024root* vlSelf) {
    (void)vlSelf;  // Prevent unused variable warning
    Vcheck__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vcheck___024root___eval_initial\n"); );
    // Body
    vlSelf->__Vtrigprevexpr___TOP__clk__0 = vlSelf->clk;
}

VL_ATTR_COLD void Vcheck___024root___eval_final(Vcheck___024root* vlSelf) {
    (void)vlSelf;  // Prevent unused variable warning
    Vcheck__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vcheck___024root___eval_final\n"); );
}

VL_ATTR_COLD void Vcheck___024root___eval_settle(Vcheck___024root* vlSelf) {
    (void)vlSelf;  // Prevent unused variable warning
    Vcheck__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vcheck___024root___eval_settle\n"); );
}

#ifdef VL_DEBUG
VL_ATTR_COLD void Vcheck___024root___dump_triggers__act(Vcheck___024root* vlSelf) {
    (void)vlSelf;  // Prevent unused variable warning
    Vcheck__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vcheck___024root___dump_triggers__act\n"); );
    // Body
    if ((1U & (~ (IData)(vlSelf->__VactTriggered.any())))) {
        VL_DBG_MSGF("         No triggers active\n");
    }
    if ((1ULL & vlSelf->__VactTriggered.word(0U))) {
        VL_DBG_MSGF("         'act' region trigger index 0 is active: @(posedge clk)\n");
    }
}
#endif  // VL_DEBUG

#ifdef VL_DEBUG
VL_ATTR_COLD void Vcheck___024root___dump_triggers__nba(Vcheck___024root* vlSelf) {
    (void)vlSelf;  // Prevent unused variable warning
    Vcheck__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vcheck___024root___dump_triggers__nba\n"); );
    // Body
    if ((1U & (~ (IData)(vlSelf->__VnbaTriggered.any())))) {
        VL_DBG_MSGF("         No triggers active\n");
    }
    if ((1ULL & vlSelf->__VnbaTriggered.word(0U))) {
        VL_DBG_MSGF("         'nba' region trigger index 0 is active: @(posedge clk)\n");
    }
}
#endif  // VL_DEBUG

VL_ATTR_COLD void Vcheck___024root___ctor_var_reset(Vcheck___024root* vlSelf) {
    (void)vlSelf;  // Prevent unused variable warning
    Vcheck__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vcheck___024root___ctor_var_reset\n"); );
    // Body
    vlSelf->clk = VL_RAND_RESET_I(1);
    vlSelf->bad = VL_RAND_RESET_I(1);
    vlSelf->__Vtrigprevexpr___TOP__clk__0 = VL_RAND_RESET_I(1);
}

// Generated file: Vcheck___024root__Slow.cpp
// Verilated -*- C++ -*-
// DESCRIPTION: Verilator output: Design implementation internals
// See Vcheck.h for the primary calling header

#include "Vcheck__pch.h"
#include "Vcheck__Syms.h"
#include "Vcheck___024root.h"

void Vcheck___024root___ctor_var_reset(Vcheck___024root* vlSelf);

Vcheck___024root::Vcheck___024root(Vcheck__Syms* symsp, const char* v__name)
    : VerilatedModule{v__name}
    , vlSymsp{symsp}
 {
    // Reset structure values
    Vcheck___024root___ctor_var_reset(this);
}

void Vcheck___024root::__Vconfigure(bool first) {
    (void)first;  // Prevent unused variable warning
}

Vcheck___024root::~Vcheck___024root() {
}
