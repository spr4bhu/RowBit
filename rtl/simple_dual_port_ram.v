// One write port, one synchronous read port; infers a block RAM.
module simple_dual_port_ram #(
    parameter WIDTH = 32,
    parameter DEPTH = 1024
) (
    input                          clk,
    input                          write_enable,
    input      [$clog2(DEPTH)-1:0] write_address,
    input      [WIDTH-1:0]         write_data,
    input      [$clog2(DEPTH)-1:0] read_address,
    output reg [WIDTH-1:0]         read_data
);
    reg [WIDTH-1:0] memory [0:DEPTH-1];

    always @(posedge clk) begin
        if (write_enable)
            memory[write_address] <= write_data;
        read_data <= memory[read_address];
    end
endmodule
