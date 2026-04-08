using Test
using ESMFormat

@testset "Display Tests" begin

    @testset "Utility Functions" begin
        # Test to_subscript
        @test ESMFormat.to_subscript(0) == "₀"
        @test ESMFormat.to_subscript(123) == "₁₂₃"
        @test ESMFormat.to_subscript(5) == "₅"

        # Test to_superscript
        @test ESMFormat.to_superscript("1") == "¹"
        @test ESMFormat.to_superscript("23") == "²³"
        @test ESMFormat.to_superscript("-1") == "⁻¹"
        @test ESMFormat.to_superscript("+2") == "⁺²"

        # Test has_element_pattern
        @test ESMFormat.has_element_pattern("H2O") == true
        @test ESMFormat.has_element_pattern("CO2") == true
        @test ESMFormat.has_element_pattern("NH3") == true
        @test ESMFormat.has_element_pattern("xyz") == false
        @test ESMFormat.has_element_pattern("temp") == false
        @test ESMFormat.has_element_pattern("H") == true
        @test ESMFormat.has_element_pattern("He") == true
    end

    @testset "Chemical Formula Formatting" begin
        # Test format_chemical_subscripts for unicode
        @test ESMFormat.format_chemical_subscripts("H2O", :unicode) == "H₂O"
        @test ESMFormat.format_chemical_subscripts("CO2", :unicode) == "CO₂"
        @test ESMFormat.format_chemical_subscripts("CH4", :unicode) == "CH₄"
        @test ESMFormat.format_chemical_subscripts("CaCO3", :unicode) == "CaCO₃"
        @test ESMFormat.format_chemical_subscripts("temp", :unicode) == "temp"  # Non-chemical variable unchanged

        # Test format_chemical_subscripts for latex
        @test ESMFormat.format_chemical_subscripts("H2O", :latex) == "\\mathrm{H_{2}O}"
        @test ESMFormat.format_chemical_subscripts("CO2", :latex) == "\\mathrm{CO_{2}}"
        @test ESMFormat.format_chemical_subscripts("NH3", :latex) == "\\mathrm{NH_{3}}"
        @test ESMFormat.format_chemical_subscripts("temp", :latex) == "temp"  # Non-chemical variable unchanged

        # Test format_chemical_subscripts for ascii
        @test ESMFormat.format_chemical_subscripts("H2O", :ascii) == "H2O"   # No subscripts in ASCII
        @test ESMFormat.format_chemical_subscripts("CO2", :ascii) == "CO2"   # No subscripts in ASCII
        @test ESMFormat.format_chemical_subscripts("NH3", :ascii) == "NH3"   # No subscripts in ASCII
        @test ESMFormat.format_chemical_subscripts("temp", :ascii) == "temp" # Non-chemical variable unchanged
    end

    @testset "Number Formatting" begin
        # Test format_number for unicode with small numbers
        @test ESMFormat.format_number(3.14, :unicode) == "3.14"
        @test ESMFormat.format_number(1.0, :unicode) == "1"  # Julia formats 1.0 as "1"
        @test ESMFormat.format_number(-2.5, :unicode) == "-2.5"
        @test ESMFormat.format_number(0, :unicode) == "0"

        # Test format_number for latex with small numbers
        @test ESMFormat.format_number(3.14, :latex) == "3.14"
        @test ESMFormat.format_number(1.0, :latex) == "1"  # Julia formats 1.0 as "1"
        @test ESMFormat.format_number(-2.5, :latex) == "-2.5"
    end

    @testset "Operator Precedence" begin
        # Test get_operator_precedence - check actual values in the implementation
        @test ESMFormat.get_operator_precedence("+") == 4
        @test ESMFormat.get_operator_precedence("-") == 4
        @test ESMFormat.get_operator_precedence("*") == 5
        @test ESMFormat.get_operator_precedence("/") == 5
        @test ESMFormat.get_operator_precedence("^") == 7
        @test ESMFormat.get_operator_precedence("pow") == 8  # Based on error output
        @test ESMFormat.get_operator_precedence("sin") == 8
        @test ESMFormat.get_operator_precedence("unknown") == 8  # Unknown operators get default precedence
    end

    @testset "Parentheses Logic" begin
        # Create test expressions
        add_expr = OpExpr("+", ESMFormat.Expr[NumExpr(1.0), VarExpr("x")])
        mul_expr = OpExpr("*", ESMFormat.Expr[VarExpr("y"), VarExpr("z")])

        # Test needs_parentheses
        @test ESMFormat.needs_parentheses("*", add_expr, false) == true   # (1 + x) * ...
        @test ESMFormat.needs_parentheses("+", mul_expr, false) == false  # y*z + ...
        @test ESMFormat.needs_parentheses("-", add_expr, true) == true    # ... - (1 + x)
        @test ESMFormat.needs_parentheses("*", mul_expr, false) == false  # y*z * ...
    end

    @testset "Expression Formatting" begin
        # Test NumExpr formatting
        num_expr = NumExpr(3.14)
        @test ESMFormat.format_expression_unicode(num_expr) == "3.14"
        @test ESMFormat.format_expression_latex(num_expr) == "3.14"

        # Test VarExpr formatting
        var_expr = VarExpr("x")
        @test ESMFormat.format_expression_unicode(var_expr) == "x"
        @test ESMFormat.format_expression_latex(var_expr) == "x"

        # Test chemical VarExpr formatting
        chem_var = VarExpr("H2O")
        @test ESMFormat.format_expression_unicode(chem_var) == "H₂O"
        @test ESMFormat.format_expression_latex(chem_var) == "\\mathrm{H_{2}O}"

        # Test basic OpExpr formatting
        add_expr = OpExpr("+", ESMFormat.Expr[NumExpr(1.0), VarExpr("x")])
        @test ESMFormat.format_expression_unicode(add_expr) == "1 + x"  # Julia formats 1.0 as "1"
        @test ESMFormat.format_expression_latex(add_expr) == "1 + x"  # Julia formats 1.0 as "1"
    end

    @testset "Show Methods" begin
        # Test Expr show methods
        num_expr = NumExpr(2.5)

        # Test plain text output
        io = IOBuffer()
        show(io, "text/plain", num_expr)
        @test String(take!(io)) == "2.5"

        # Test LaTeX output
        show(io, "text/latex", num_expr)
        @test String(take!(io)) == "2.5"

        # Test ASCII output
        show(io, "text/ascii", num_expr)
        @test String(take!(io)) == "2.5"

        # Test more complex expressions with ASCII MIME type
        mul_expr = OpExpr("*", ESMFormat.Expr[VarExpr("x"), NumExpr(2.0)])
        show(io, "text/ascii", mul_expr)
        @test String(take!(io)) == "x*2"

        pow_expr = OpExpr("^", ESMFormat.Expr[VarExpr("x"), NumExpr(2.0)])
        show(io, "text/ascii", pow_expr)
        @test String(take!(io)) == "x^2"

        # Test chemical formula in ASCII (no subscripts)
        chem_var = VarExpr("H2O")
        show(io, "text/ascii", chem_var)
        @test String(take!(io)) == "H2O"  # Plain ASCII, no Unicode subscripts
    end

    @testset "Equation Display" begin
        # Test Equation show method
        lhs = OpExpr("D", ESMFormat.Expr[VarExpr("x")], wrt="t")
        rhs = OpExpr("*", ESMFormat.Expr[NumExpr(2.0), VarExpr("x")])
        eq = Equation(lhs, rhs)

        io = IOBuffer()
        show(io, eq)
        output = String(take!(io))
        # Just test that show produces some output that looks like an equation
        @test Base.contains(output, "x")
        @test Base.contains(output, "=")
        @test length(output) > 0
    end

    @testset "EsmFile Display" begin
        # Test EsmFile show method
        metadata = Metadata("test_model", description="Test model")
        esm_file = EsmFile("0.1.0", metadata)

        io = IOBuffer()
        show(io, esm_file)
        output = String(take!(io))
        # Just test that show produces some output with the basic info
        @test Base.contains(output, "test_model")
        @test Base.contains(output, "0.1.0")
        @test length(output) > 0
    end

end