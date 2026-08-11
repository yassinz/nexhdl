from nexhdl import Module, INPUT, OUTPUT, Logic, Struct, Array, clog2

class Point[WIDTH: int](Struct):
    """A point in 2D space."""
    x: Logic[WIDTH]
    y: Logic[WIDTH]

    def __add__(self, other):
        return Point[WIDTH](x=self.x + other.x, y=self.y + other.y)

class Rectangle[WIDTH: int](Struct):
    """A rectangle defined by its origin (top-left) and dimensions."""
    origin: Point[WIDTH]
    width:  Logic[WIDTH]
    height: Logic[WIDTH]

class GeometryProcessor[COUNT: int, WIDTH: int](Module):
    """
    A module that manages an array of geometric shapes.
    Demonstrates:
    1. Parameterized Structs (Point[WIDTH], Rectangle[WIDTH])
    2. Nested Structs (Rectangle contains a Point)
    3. Arrays of Structs (Array[COUNT, Rectangle])
    4. Struct operator overloading (Point.__add__)
    5. Simulation of complex nested types using Python dictionaries and lists.
    """
    sel:         INPUT[Logic[clog2(COUNT)]]
    offset:      INPUT[Point[WIDTH]]
    
    # The selected and transformed rectangle
    rect_out:    OUTPUT[Rectangle[WIDTH]]
    # Area of the selected rectangle
    area_out:    OUTPUT[Logic[WIDTH * 2]]

    def build(self, io):
        # 1. Create a collection of rectangles
        rect_list = []
        for i in range(COUNT):
             rect_list.append(Rectangle[WIDTH](
                 origin = Point[WIDTH](x=i*10, y=i*10),
                 width  = Logic[WIDTH](10 * (i + 1)),
                 height = Logic[WIDTH](20 * (i + 1))
             ))
        
        # 2. Represent them as an NexHDL Array
        shapes = Array[COUNT, Rectangle[WIDTH]](rect_list)
        
        # 3. Dynamic indexing into the array of structs
        selected = shapes[io.sel]
        
        # 4. Use operator overloading and nested field access
        # We translate the origin by the input offset
        translated_origin = selected.origin + io.offset
        
        # 5. Output the transformed rectangle
        io.rect_out = Rectangle[WIDTH](
            origin = translated_origin,
            width  = selected.width,
            height = selected.height
        )
        
        # 6. Compute area (demonstrates arithmetic on struct fields)
        io.area_out = selected.width.zext(WIDTH*2) * selected.height.zext(WIDTH*2)

if __name__ == "__main__":
    # Create a processor for 4 rectangles using 16-bit coordinates
    WIDTH = 16
    COUNT = 4
    proc = GeometryProcessor[COUNT, WIDTH]()
    
    print(f"--- Verilog for GeometryProcessor[{COUNT}, {WIDTH}] ---")
    print(proc.verilog())
    
    print("\n--- Starting Simulation ---")
    with proc.simulate() as sim:
        # Test Case 1: Select rectangle 0, no offset
        sim.io.sel = 0
        sim.io.offset = {'x': 0, 'y': 0}
        sim.step()
        print(f"Rect[0]: {sim.io.rect_out}, Area: {sim.io.area_out}")
        assert sim.io.rect_out['origin'] == {'x': 0, 'y': 0}
        assert sim.io.area_out == 10 * 20

        # Test Case 2: Select rectangle 2, apply offset
        # Rect[2] base origin is (20, 20), width=30, height=60
        sim.io.sel = 2
        sim.io.offset = {'x': 5, 'y': 15}
        sim.step()
        print(f"Rect[2] with offset (5, 15): {sim.io.rect_out}, Area: {sim.io.area_out}")
        
        expected_origin = {'x': 20 + 5, 'y': 20 + 15}
        assert sim.io.rect_out['origin'] == expected_origin
        assert sim.io.rect_out['width'] == 30
        assert sim.io.rect_out['height'] == 60
        assert sim.io.area_out == 30 * 60

        print("\n✓ Simulation Successful!")
