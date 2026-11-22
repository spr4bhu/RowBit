// Plays a program of DDR3 commands onto LiteDRAM's DFI, 4 command slots (one per DRAM clock) per sys clock.
module dram_sequencer #(
    parameter ADDRESS_BITS  = 14,
    parameter BANK_BITS     = 3,
    parameter PROGRAM_DEPTH = 1024,
    parameter WRITE_DEPTH   = 512,
    parameter READ_DEPTH    = 2048,
    parameter WRITE_LATENCY = 1,   // sys cycles from a WR command to its data on DFI
    parameter DRAIN_CYCLES  = 16,  // longer than the read latency, so the last reads land
    parameter REFRESH_RECOVERY_CYCLES = 16  // >= tRFC after the controller's REF (160 ns at 75 MHz)
) (
    input clk,
    input rst,

    // Wishbone slave (32-bit words); only full-word writes are supported.
    input      [29:0] wb_adr,
    input      [31:0] wb_dat_w,
    output reg [31:0] wb_dat_r,
    input             wb_cyc,
    input             wb_stb,
    input             wb_we,
    output reg        wb_ack,

    // Memory controller's phase-0 command, watched for its refresh.
    input ctrl_cs_n,
    input ctrl_ras_n,
    input ctrl_cas_n,
    input ctrl_we_n,

    // DFI master; phase p uses bits [p*WIDTH +: WIDTH].
    output reg                      dfi_select,
    output reg [4*ADDRESS_BITS-1:0] dfi_address,
    output reg [4*BANK_BITS-1:0]    dfi_bank,
    output reg [3:0]                dfi_cs_n,
    output reg [3:0]                dfi_ras_n,
    output reg [3:0]                dfi_cas_n,
    output reg [3:0]                dfi_we_n,
    output reg [3:0]                dfi_wrdata_en,
    output reg [3:0]                dfi_rddata_en,
    output     [127:0]              dfi_wrdata,
    output     [15:0]               dfi_wrdata_mask,
    output     [3:0]                dfi_cke,
    output     [3:0]                dfi_odt,
    output     [3:0]                dfi_reset_n,
    input      [127:0]              dfi_rddata,
    input                           dfi_rddata_valid
);
    localparam ACT = 3'd1, PRE = 3'd2, RD = 3'd3, WR = 3'd4, REF = 3'd5, ZQCS = 3'd6;
    localparam IDLE = 2'd0, WAIT_REFRESH = 2'd1, RUN = 2'd2, DRAIN = 2'd3;
    localparam PROGRAM_BITS = $clog2(PROGRAM_DEPTH);
    localparam WRITE_BITS   = $clog2(WRITE_DEPTH);
    localparam READ_BITS    = $clog2(READ_DEPTH);

    assign dfi_wrdata_mask = 16'h0000;
    assign dfi_cke         = 4'b1111;
    assign dfi_odt         = 4'b1111;
    assign dfi_reset_n     = 4'b1111;

    function bundle_has(input [127:0] bundle, input [2:0] command);
        integer s;
        begin
            bundle_has = 1'b0;
            for (s = 0; s < 4; s = s + 1)
                bundle_has = bundle_has | bundle[24*s +: 3] == command;
        end
    endfunction

    // {cs_n, ras_n, cas_n, we_n} for each command.
    function [3:0] control_pins(input [2:0] command);
        case (command)
            ACT:     control_pins = 4'b0011;
            PRE:     control_pins = 4'b0010;
            RD:      control_pins = 4'b0101;
            WR:      control_pins = 4'b0100;
            REF:     control_pins = 4'b0001;
            ZQCS:    control_pins = 4'b0110;
            default: control_pins = 4'b1111;
        endcase
    endfunction

    // ---- bus decode
    wire        bus_write      = wb_cyc & wb_stb & wb_we & ~wb_ack;
    wire [1:0]  bus_region     = wb_adr[15:14];
    wire [1:0]  bus_lane       = wb_adr[1:0];
    wire [11:0] bus_entry      = wb_adr[13:2];

    // ---- state
    reg [1:0]              state;
    reg                    done;
    reg [31:0]             program_length;
    reg [PROGRAM_BITS-1:0] pc;
    reg                    last_issued;
    reg [31:0]             wait_count;
    reg [$clog2(DRAIN_CYCLES+1)-1:0] drain_count;
    reg [WRITE_BITS:0]     write_count;
    reg [READ_BITS:0]      read_count;
    reg [READ_BITS:0]      expected_reads;
    wire                   program_fits = program_length != 0 & program_length <= PROGRAM_DEPTH;
    wire                   start        = bus_write & bus_region == 2'd0 & bus_lane == 2'd0 & wb_dat_w[0] &
                                          state == IDLE;

    // ---- program memory: 4 lanes of 32 bits form one 128-bit instruction
    wire [127:0] instruction;
    wire         issue = state == RUN & wait_count == 0 & ~last_issued;
    wire [PROGRAM_BITS-1:0] pc_next = start ? 0 : issue ? pc + 1'b1 : pc;

    // ---- write data memory: each bundle with a WR takes the next 128-bit entry
    wire [127:0] write_entry;
    reg  [127:0] write_pipeline [0:WRITE_LATENCY-1];
    assign dfi_wrdata = write_pipeline[WRITE_LATENCY-1];

    // ---- read data memory: only bursts answering our own RDs are stored
    wire        capture = dfi_select & dfi_rddata_valid & read_count != expected_reads;
    wire [31:0] read_lane [0:3];
    reg  [1:0]  read_lane_selected;

    genvar lane;
    generate
        for (lane = 0; lane < 4; lane = lane + 1) begin : lanes
            simple_dual_port_ram #(.WIDTH(32), .DEPTH(PROGRAM_DEPTH)) program_ram (
                .clk(clk),
                .write_enable(bus_write & bus_region == 2'd1 & bus_lane == lane),
                .write_address(bus_entry[PROGRAM_BITS-1:0]), .write_data(wb_dat_w),
                .read_address(pc_next), .read_data(instruction[32*lane +: 32]));

            simple_dual_port_ram #(.WIDTH(32), .DEPTH(WRITE_DEPTH)) write_ram (
                .clk(clk),
                .write_enable(bus_write & bus_region == 2'd2 & bus_lane == lane),
                .write_address(bus_entry[WRITE_BITS-1:0]), .write_data(wb_dat_w),
                .read_address(write_count[WRITE_BITS-1:0]), .read_data(write_entry[32*lane +: 32]));

            simple_dual_port_ram #(.WIDTH(32), .DEPTH(READ_DEPTH)) read_ram (
                .clk(clk),
                .write_enable(capture),
                .write_address(read_count[READ_BITS-1:0]), .write_data(dfi_rddata[32*lane +: 32]),
                .read_address(bus_entry[READ_BITS-1:0]), .read_data(read_lane[lane]));
        end
    endgenerate

    // ---- write data delay: RAM read is 1 cycle, the rest is registers
    integer stage;
    always @(posedge clk) begin
        write_pipeline[0] <= write_entry;
        for (stage = 1; stage < WRITE_LATENCY; stage = stage + 1)
            write_pipeline[stage] <= write_pipeline[stage - 1];
    end

    // ---- sequencing
    wire controller_refresh = ~ctrl_cs_n & ~ctrl_ras_n & ~ctrl_cas_n & ctrl_we_n;
    integer slot;

    always @(posedge clk) begin
        // Every slot is NOP unless this cycle issues a bundle.
        dfi_cs_n      <= 4'b1111;
        dfi_ras_n     <= 4'b1111;
        dfi_cas_n     <= 4'b1111;
        dfi_we_n      <= 4'b1111;
        dfi_wrdata_en <= 4'b0000;
        dfi_rddata_en <= 4'b0000;

        if (rst) begin
            state       <= IDLE;
            done        <= 1'b0;
            dfi_select  <= 1'b0;
            dfi_bank    <= 0;
            dfi_address <= 0;
            pc          <= 0;
            write_count <= 0;
            read_count  <= 0;
        end else begin
            pc <= pc_next;
            if (capture)
                read_count <= read_count + 1'b1;

            case (state)
                IDLE: if (start) begin
                    done           <= ~program_fits;
                    state          <= program_fits ? WAIT_REFRESH : IDLE;
                    last_issued    <= 1'b0;
                    write_count    <= 0;
                    read_count     <= 0;
                    expected_reads <= 0;
                end
                WAIT_REFRESH: if (controller_refresh) begin
                    state      <= RUN;
                    dfi_select <= 1'b1;
                    wait_count <= REFRESH_RECOVERY_CYCLES;
                end
                RUN: if (wait_count != 0) begin
                    wait_count <= wait_count - 1'b1;
                end else if (last_issued) begin
                    state       <= DRAIN;
                    drain_count <= DRAIN_CYCLES;
                end else begin
                    for (slot = 0; slot < 4; slot = slot + 1) begin
                        {dfi_cs_n[slot], dfi_ras_n[slot], dfi_cas_n[slot], dfi_we_n[slot]}
                            <= control_pins(instruction[24*slot +: 3]);
                        dfi_bank[BANK_BITS*slot +: BANK_BITS]          <= instruction[24*slot + 3 +: BANK_BITS];
                        dfi_address[ADDRESS_BITS*slot +: ADDRESS_BITS] <= instruction[24*slot + 6 +: ADDRESS_BITS];
                        dfi_wrdata_en[slot] <= instruction[24*slot +: 3] == WR;
                        dfi_rddata_en[slot] <= instruction[24*slot +: 3] == RD;
                    end
                    if (bundle_has(instruction, WR))
                        write_count <= write_count + 1'b1;
                    if (bundle_has(instruction, RD))
                        expected_reads <= expected_reads + 1'b1;
                    wait_count  <= instruction[127:96];
                    last_issued <= {{(32 - PROGRAM_BITS){1'b0}}, pc} == program_length - 1;
                end
                DRAIN: if (drain_count == 0) begin
                    state      <= IDLE;
                    dfi_select <= 1'b0;
                    done       <= 1'b1;
                end else begin
                    drain_count <= drain_count - 1'b1;
                end
            endcase
        end
    end

    // ---- bus: registers and RAMs answer one cycle after the request
    always @(posedge clk) begin
        wb_ack <= ~rst & wb_cyc & wb_stb & ~wb_ack;
        read_lane_selected <= bus_lane;
        if (rst)
            program_length <= 0;
        else if (bus_write & bus_region == 2'd0 & bus_lane == 2'd1)
            program_length <= wb_dat_w;
    end

    reg [1:0]  bus_region_q;
    reg [31:0] register_value;
    always @(posedge clk) begin
        bus_region_q <= bus_region;
        case (bus_lane)
            2'd0:    register_value <= {30'b0, done, state != IDLE};
            2'd1:    register_value <= program_length;
            2'd2:    register_value <= {{(31 - READ_BITS){1'b0}}, read_count};
            default: register_value <= {{(31 - WRITE_BITS){1'b0}}, write_count};
        endcase
    end

    always @(*)
        wb_dat_r = bus_region_q == 2'd3 ? read_lane[read_lane_selected] : register_value;
endmodule
