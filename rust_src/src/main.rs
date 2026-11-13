pub mod hello_world {
    trait HelloWorlatable {
        fn hello_world() -> () {}
    }

    pub fn hello_world() -> () {
        print!("hello-world from rust!")
    }

    pub struct HelloWorlder {}

    impl HelloWorlatable for HelloWorlder {
        fn hello_world() {
            hello_world()
        }
    }
}

fn main() {
    hello_world::hello_world;
}
